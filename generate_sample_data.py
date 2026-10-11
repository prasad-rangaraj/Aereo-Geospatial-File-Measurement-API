"""Generate sample datasets for testing and reviewer demonstration:
1. survey_bengaluru.kml
2. cadastral_parcels.zip (Shapefile)
3. road_network.kml
4. invalid_corrupt.zip
"""
import io
import os
import zipfile
from pathlib import Path
import shapefile

SAMPLE_DIR = Path(__file__).resolve().parent / "sample_data"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

def generate_kml_survey():
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Bengaluru Tech Park Drone Survey</name>
    <description>Drone photogrammetry survey of land parcels, haul roads, and RTK base station</description>

    <!-- Polygon 1: Zone A Construction Site -->
    <Placemark>
      <name>Zone A - Construction Site</name>
      <description>Heavy earthmoving and foundation zone</description>
      <ExtendedData>
        <Data name="contractor"><value>Aereo Engineering</value></Data>
        <Data name="phase"><value>Phase 1 Foundation</value></Data>
        <Data name="classification"><value>Commercial</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.5920,12.9700,920
              77.5960,12.9700,920
              77.5960,12.9740,922
              77.5920,12.9740,921
              77.5920,12.9700,920
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>

    <!-- Polygon 2: Zone B Solar Array (with inner retention pond hole) -->
    <Placemark>
      <name>Zone B - Solar Farm with Retention Basin</name>
      <description>Rooftop solar and ground mount photovoltaic field</description>
      <ExtendedData>
        <Data name="capacity_mw"><value>4.5</value></Data>
        <Data name="panel_type"><value>Monocrystalline</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.5970,12.9700,918
              77.6000,12.9700,918
              77.6000,12.9730,919
              77.5970,12.9730,919
              77.5970,12.9700,918
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
        <innerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.5980,12.9710,915
              77.5990,12.9710,915
              77.5990,12.9720,915
              77.5980,12.9720,915
              77.5980,12.9710,915
            </coordinates>
          </LinearRing>
        </innerBoundaryIs>
      </Polygon>
    </Placemark>

    <!-- LineString: Primary Haul Road -->
    <Placemark>
      <name>Primary Haul Road</name>
      <description>Heavy machinery arterial access route</description>
      <ExtendedData>
        <Data name="surface"><value>Reinforced Concrete</value></Data>
        <Data name="max_weight_tons"><value>60</value></Data>
      </ExtendedData>
      <LineString>
        <coordinates>
          77.5910,12.9690,919
          77.5940,12.9720,921
          77.5980,12.9725,920
          77.6020,12.9750,923
        </coordinates>
      </LineString>
    </Placemark>

    <!-- Point: Drone Base Station -->
    <Placemark>
      <name>RTK GNSS Base Station</name>
      <description>Triple-frequency RTK base station for drone positioning</description>
      <ExtendedData>
        <Data name="station_id"><value>BLR-RTK-01</value></Data>
        <Data name="elevation_msl"><value>924.35</value></Data>
      </ExtendedData>
      <Point>
        <coordinates>77.5950,12.9720,924.35</coordinates>
      </Point>
    </Placemark>

  </Document>
</kml>
"""
    output_path = SAMPLE_DIR / "survey_bengaluru.kml"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(kml_content)
    print(f"Generated: {output_path}")

def generate_shapefile_zip():
    shp_buf = io.BytesIO()
    shx_buf = io.BytesIO()
    dbf_buf = io.BytesIO()

    w = shapefile.Writer(shp=shp_buf, shx=shx_buf, dbf=dbf_buf, shapeType=shapefile.POLYGON)
    w.field('parcel_id', 'C', size=20)
    w.field('owner', 'C', size=50)
    w.field('land_use', 'C', size=30)
    w.field('tax_value', 'N', decimal=2)

    # Parcel 1: North Agricultural Tract (Clockwise ring)
    w.poly([[[77.5850, 12.9600], [77.5850, 12.9640], [77.5890, 12.9640], [77.5890, 12.9600], [77.5850, 12.9600]]])
    w.record('P-1001', 'Aereo Farmlands Ltd', 'Agriculture', 450000.00)

    # Parcel 2: South Industrial Park (Clockwise ring)
    w.poly([[[77.5900, 12.9600], [77.5900, 12.9630], [77.5940, 12.9630], [77.5940, 12.9600], [77.5900, 12.9600]]])
    w.record('P-1002', 'Karnataka Industrial Infra', 'Industrial', 1250000.00)

    # Parcel 3: Commercial Hub (Clockwise ring)
    w.poly([[[77.5850, 12.9650], [77.5850, 12.9690], [77.5880, 12.9690], [77.5880, 12.9650], [77.5850, 12.9650]]])
    w.record('P-1003', 'Metro Urban Center', 'Commercial', 3400000.00)

    w.close()

    prj_wkt = (
        'GEOGCS["GCS_WGS_1984",'
        'DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
        'PRIMEM["Greenwich",0.0],'
        'UNIT["Degree",0.0174532925199433]]'
    )

    zip_path = SAMPLE_DIR / "cadastral_parcels.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("cadastral_parcels.shp", shp_buf.getvalue())
        zf.writestr("cadastral_parcels.shx", shx_buf.getvalue())
        zf.writestr("cadastral_parcels.dbf", dbf_buf.getvalue())
        zf.writestr("cadastral_parcels.prj", prj_wkt)

    print(f"Generated: {zip_path}")

def generate_road_network_kml():
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Survey Road Infrastructure Network</name>
    <Placemark>
      <name>Outer Ring Perimeter Road</name>
      <LineString>
        <coordinates>
          77.5800,12.9550,0
          77.5850,12.9600,0
          77.5900,12.9650,0
          77.5950,12.9700,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Spur Line 1</name>
      <LineString>
        <coordinates>
          77.5850,12.9600,0
          77.5880,12.9580,0
          77.5920,12.9580,0
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
"""
    output_path = SAMPLE_DIR / "road_network.kml"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(kml_content)
    print(f"Generated: {output_path}")

def generate_corrupt_zip():
    zip_path = SAMPLE_DIR / "invalid_corrupt.zip"
    with open(zip_path, "wb") as f:
        f.write(b"PK\x03\x04CORRUPTED_ZIP_BINARY_DATA_NON_ARCHIVE")
    print(f"Generated: {zip_path}")

if __name__ == "__main__":
    generate_kml_survey()
    generate_shapefile_zip()
    generate_road_network_kml()
    generate_corrupt_zip()
    print("All sample data fixtures created successfully.")
