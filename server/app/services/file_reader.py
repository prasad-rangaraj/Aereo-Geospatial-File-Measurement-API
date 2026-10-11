"""File readers for geospatial formats: Shapefile (.zip) and KML (.kml)."""
import io
import os
import zipfile
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import defusedxml.ElementTree as ET
import shapefile
import shapely
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, MultiLineString, MultiPoint, shape, mapping
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger("aereo.file_reader")

@dataclass
class ExtractedFeature:
    index: int
    identifier: Optional[str]
    geometry_type: str
    geometry: BaseGeometry
    properties: Dict[str, Any]
    geojson_geometry: Dict[str, Any]


@dataclass
class ExtractedDataset:
    filename: str
    file_type: str
    source_crs_raw: Optional[str]
    features: List[ExtractedFeature]
    bounds: Optional[List[float]]
    warnings: List[str]


class GeospatialReaderError(Exception):
    """Base exception for file parsing errors."""
    pass


def _parse_kml_coordinates(coord_text: str) -> List[Tuple[float, ...]]:
    """Parse a KML coordinates whitespace/comma-delimited string into coordinate tuples."""
    coords: List[Tuple[float, ...]] = []
    if not coord_text:
        return coords
    
    # Coordinates in KML are whitespace-separated tuples of lon,lat[,alt]
    items = coord_text.strip().split()
    for item in items:
        parts = [p.strip() for p in item.split(',') if p.strip()]
        if len(parts) >= 2:
            try:
                lon = float(parts[0])
                lat = float(parts[1])
                if len(parts) >= 3:
                    alt = float(parts[2])
                    coords.append((lon, lat, alt))
                else:
                    coords.append((lon, lat))
            except ValueError:
                continue
    return coords


def _parse_kml_polygon(poly_node: ET.Element) -> Optional[Polygon]:
    """Parse KML Polygon including outer boundary and interior hole boundaries."""
    outer_node = poly_node.find('.//outerBoundaryIs//LinearRing//coordinates')
    if outer_node is None or not outer_node.text:
        return None
    
    outer_coords = _parse_kml_coordinates(outer_node.text)
    if len(outer_coords) < 3:
        return None
    
    # Parse inner holes if any
    inner_holes: List[List[Tuple[float, ...]]] = []
    for inner_node in poly_node.findall('.//innerBoundaryIs//LinearRing//coordinates'):
        if inner_node.text:
            inner_coords = _parse_kml_coordinates(inner_node.text)
            if len(inner_coords) >= 3:
                inner_holes.append(inner_coords)
                
    try:
        return Polygon(shell=outer_coords, holes=inner_holes)
    except Exception as e:
        logger.warning(f"Failed to create Polygon from KML coordinates: {e}")
        return None


def read_kml_content(content_bytes: bytes, filename: str) -> ExtractedDataset:
    """Read and extract all spatial features and metadata from a KML file."""
    try:
        root = ET.fromstring(content_bytes)
    except Exception as e:
        raise GeospatialReaderError(f"Malformed or invalid KML file: {str(e)}") from e

    # Strip XML namespace prefixes for uniform traversal
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]

    features: List[ExtractedFeature] = []
    warnings: List[str] = []
    
    # OGC KML standard is strictly WGS 84 geographic coordinates
    source_crs = "EPSG:4326"
    
    placemarks = root.findall('.//Placemark')
    feature_index = 0
    
    for p in placemarks:
        name = p.findtext('name', default=None)
        description = p.findtext('description', default=None)
        
        properties: Dict[str, Any] = {}
        if name:
            properties['name'] = name.strip()
        if description:
            properties['description'] = description.strip()

        # Parse ExtendedData (name-value pairs)
        for data in p.findall('.//ExtendedData//Data'):
            attr_name = data.attrib.get('name')
            val = data.findtext('value')
            if attr_name and val:
                properties[attr_name] = val.strip()

        for sdata in p.findall('.//ExtendedData//SimpleData'):
            attr_name = sdata.attrib.get('name')
            val = sdata.text
            if attr_name and val:
                properties[attr_name] = val.strip()

        # Search for geometry types within this placemark
        geoms_found: List[BaseGeometry] = []
        
        # 1. Polygon(s)
        for poly_node in p.findall('.//Polygon'):
            poly = _parse_kml_polygon(poly_node)
            if poly and not poly.is_empty:
                geoms_found.append(poly)
                
        # 2. LineString(s)
        for line_node in p.findall('.//LineString'):
            coord_node = line_node.find('.//coordinates')
            if coord_node is not None and coord_node.text:
                coords = _parse_kml_coordinates(coord_node.text)
                if len(coords) >= 2:
                    geoms_found.append(LineString(coords))

        # 3. Point(s)
        for pt_node in p.findall('.//Point'):
            coord_node = pt_node.find('.//coordinates')
            if coord_node is not None and coord_node.text:
                coords = _parse_kml_coordinates(coord_node.text)
                if coords:
                    geoms_found.append(Point(coords[0]))

        if not geoms_found:
            continue

        for geom in geoms_found:
            geojson_geom = mapping(geom)
            features.append(
                ExtractedFeature(
                    index=feature_index,
                    identifier=name or f"Feature_{feature_index}",
                    geometry_type=geom.geom_type,
                    geometry=geom,
                    properties=properties,
                    geojson_geometry=geojson_geom
                )
            )
            feature_index += 1

    if not features:
        warnings.append("No valid vector geometries (Polygon, LineString, Point) found in KML file.")

    # Calculate overall bounding box
    bounds = None
    if features:
        all_geoms = [f.geometry for f in features]
        total_bounds = shapely.total_bounds(all_geoms)
        bounds = [float(b) for b in total_bounds]

    return ExtractedDataset(
        filename=filename,
        file_type="kml",
        source_crs_raw=source_crs,
        features=features,
        bounds=bounds,
        warnings=warnings
    )


def read_shapefile_zip(content_bytes: bytes, filename: str) -> ExtractedDataset:
    """Read and extract features from a ZIP archive containing an ESRI Shapefile."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(content_bytes))
    except Exception as e:
        raise GeospatialReaderError(f"Uploaded file is not a valid ZIP archive: {str(e)}") from e

    file_names = zf.namelist()
    shp_files = [f for f in file_names if f.lower().endswith('.shp') and not f.startswith('__MACOSX')]
    
    if not shp_files:
        raise GeospatialReaderError("Invalid Shapefile archive: missing required .shp file.")

    shp_path = shp_files[0]
    base_prefix = shp_path[:-4]
    
    # Check for companion files
    shx_matches = [f for f in file_names if f.lower() == (base_prefix.lower() + '.shx')]
    dbf_matches = [f for f in file_names if f.lower() == (base_prefix.lower() + '.dbf')]
    prj_matches = [f for f in file_names if f.lower() == (base_prefix.lower() + '.prj')]

    if not shx_matches:
        raise GeospatialReaderError(f"Incomplete Shapefile: companion index file '{base_prefix}.shx' is missing.")
    if not dbf_matches:
        raise GeospatialReaderError(f"Incomplete Shapefile: companion attributes table '{base_prefix}.dbf' is missing.")

    warnings: List[str] = []
    source_crs_raw: Optional[str] = None

    if prj_matches:
        try:
            prj_bytes = zf.read(prj_matches[0])
            source_crs_raw = prj_bytes.decode('utf-8', errors='ignore').strip()
        except Exception as e:
            warnings.append(f"Failed to read .prj coordinate projection metadata: {e}")
    else:
        warnings.append("No .prj projection file found in Shapefile archive. Missing CRS will default to EPSG:4326.")

    try:
        with zf.open(shp_path) as s, zf.open(shx_matches[0]) as sx, zf.open(dbf_matches[0]) as d:
            r = shapefile.Reader(shp=s, shx=sx, dbf=d, encoding="utf-8", encodingErrors="replace")
            
            features: List[ExtractedFeature] = []
            for i, shape_rec in enumerate(r.shapeRecords()):
                shp_obj = shape_rec.shape
                # If shape has no points or is null
                if not hasattr(shp_obj, 'points') or len(shp_obj.points) == 0:
                    continue
                
                try:
                    geom = shape(shp_obj.__geo_interface__)
                    if geom.is_empty:
                        continue
                except Exception as e:
                    logger.warning(f"Could not convert shape record #{i} to geometry: {e}")
                    continue

                record_props = shape_rec.record.as_dict()
                # Clean up any non-serializable values
                clean_props = {str(k): (v if not isinstance(v, bytes) else v.decode('utf-8', 'ignore')) for k, v in record_props.items()}
                identifier = clean_props.get('name') or clean_props.get('id') or clean_props.get('ID') or f"Feature_{i}"

                features.append(
                    ExtractedFeature(
                        index=i,
                        identifier=str(identifier),
                        geometry_type=geom.geom_type,
                        geometry=geom,
                        properties=clean_props,
                        geojson_geometry=mapping(geom)
                    )
                )

    except Exception as e:
        raise GeospatialReaderError(f"Failed to read ESRI Shapefile records: {str(e)}") from e

    bounds = None
    if features:
        all_geoms = [f.geometry for f in features]
        total_bounds = shapely.total_bounds(all_geoms)
        bounds = [float(b) for b in total_bounds]

    return ExtractedDataset(
        filename=filename,
        file_type="shapefile",
        source_crs_raw=source_crs_raw,
        features=features,
        bounds=bounds,
        warnings=warnings
    )
