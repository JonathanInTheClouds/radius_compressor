import math
from math import sin, cos, asin, atan2, radians as rad, degrees as deg

CENTER_LAT = 34.73
CENTER_LON = -86.59
LINE_LENGTH_MILES = 900
HUB_RADIUS_MILES = 2

ANCHOR_SPACING_MILES = 0.5
NUM_DUPLICATES = 25

START_HEIGHT = 5000
HEIGHT_OFFSET = 2000

CRUISE_SPEED = 1200
TURN_SPEED = 120

OUTPUT_FILENAME = "colored_speed_spiral_lol.kml"

def get_rotation_step(r, gap):
    return deg(gap / r) if r else 0

def get_dest(lat, lon, dist, bear):
    l1, n1, b, ad = rad(lat), rad(lon), rad(bear), dist / 3958.8
    l2 = asin(sin(l1)*cos(ad) + cos(l1)*sin(ad)*cos(b))
    n2 = n1 + atan2(sin(b)*sin(ad)*cos(l1), cos(ad)-sin(l1)*sin(l2))
    return deg(l2), deg(n2)

def densify(la1, lo1, la2, lo2, n=20):
    return [(la1+(la2-la1)*i/n, lo1+(lo2-lo1)*i/n) for i in range(n+1)]

def get_corners(lat, lon, r, rot):
    c = get_dest(lat, lon, r, 270 + rot)
    return {
        "North": get_dest(*c, r, rot),
        "East":  (lat, lon),
        "South": get_dest(*c, r, 180 + rot),
        "West":  get_dest(*c, r, 270 + rot)
    }

def tessellate_with_variable_speed(c, alt):
    order = ["North", "East", "South", "West", "North"]
    full_path_data = []
    segments = 20

    for i in range(4):
        start_key = order[i]
        end_key = order[i+1]
        
        raw_pts = densify(*c[start_key], *c[end_key], segments)
        
        for j, (lat, lon) in enumerate(raw_pts):
            is_last_two = (j >= len(raw_pts) - 2)
            is_first_two = (j < 2)
            current_speed = CRUISE_SPEED

            if i == 0:
                if is_last_two:
                    current_speed = TURN_SPEED
            else:
                if is_first_two or is_last_two:
                    current_speed = TURN_SPEED
            
            full_path_data.append({
                'lat': lat,
                'lon': lon,
                'spd': current_speed,
                'alt': alt
            })

    return full_path_data

def create_kml(diamonds, center, filename):
    header = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
        ' <Style id="fast"><IconStyle><scale>0.5</scale><color>ff00ff00</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>',
        ' <Style id="slow"><IconStyle><scale>0.7</scale><color>ff0000ff</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>',
        ' <Style id="poly"><LineStyle><color>77ffffff</color><width>1</width></LineStyle><PolyStyle><color>00000000</color></PolyStyle></Style>',
        ' <Style id="h"><IconStyle><scale>1.2</scale></IconStyle></Style>'
    ]
    body = []

    body.append(f'<Placemark><name>Hub</name><styleUrl>#h</styleUrl><Point><coordinates>{center[1]},{center[0]},0</coordinates></Point></Placemark>')

    body.append('<Folder><name>Shapes</name>')
    for i, d in enumerate(diamonds):
        coords = " ".join([f"{p['lon']:.5f},{p['lat']:.5f},{p['alt']}" for p in d['path']])
        body.append(f"""
        <Placemark>
          <name>D{i+1} Polygon</name>
          <styleUrl>#poly</styleUrl>
          <Polygon><altitudeMode>absolute</altitudeMode><tessellate>1</tessellate>
            <outerBoundaryIs><LinearRing><coordinates>{coords}</coordinates></LinearRing></outerBoundaryIs>
          </Polygon>
        </Placemark>""")
    body.append('</Folder>')

    body.append('<Folder><name>Waypoints</name>')
    for i, d in enumerate(diamonds):
        body.append(f'<Folder><name>Diamond {i+1} Points</name>')
        
        for j, p in enumerate(d['path']): 
            speed = p['spd']
            alt = p['alt']
            style_id = "#slow" if speed == TURN_SPEED else "#fast"
            
            body.append(f"""
            <Placemark>
              <name>Pt {j}</name>
              <description>Speed: {speed} mph\nAlt: {alt}</description>
              <styleUrl>{style_id}</styleUrl>
              <Point><altitudeMode>absolute</altitudeMode><coordinates>{p['lon']:.5f},{p['lat']:.5f},{alt}</coordinates></Point>
            </Placemark>""")
            
        body.append('</Folder>')
        
    body.append('</Folder>')

    with open(filename, "w") as f:
        f.write("\n".join(header + body + ['</Document></kml>']))
    print(f"\n[System] Saved KML file: {filename}")

diamonds = []
rot_step = get_rotation_step(HUB_RADIUS_MILES, ANCHOR_SPACING_MILES)

print(f"{'='*50}\nGENERATING COLORED SPEED SPIRAL\n{'='*50}")

for i in range(NUM_DUPLICATES):
    cur_rot = i * rot_step
    cur_alt = START_HEIGHT + (i * HEIGHT_OFFSET)
    
    anchor = get_dest(CENTER_LAT, CENTER_LON, HUB_RADIUS_MILES, cur_rot)
    corners = get_corners(anchor[0], anchor[1], LINE_LENGTH_MILES, cur_rot)
    
    path_data = tessellate_with_variable_speed(corners, cur_alt)
    
    diamonds.append({
        'path': path_data
    })
    
    print(f"Diamond {i+1}: {len(path_data)} points processed.")

create_kml(diamonds, (CENTER_LAT, CENTER_LON), OUTPUT_FILENAME)