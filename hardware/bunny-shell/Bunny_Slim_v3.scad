// Ceramic-look bunny barrette fit prototype, millimeters.
// Screen aperture is provisional. Adjust after measuring the active area.
$fn = 48;

window_width = 43.5;
window_height = 23.5;
window_x = 0;
window_y = 0;
bezel_depth = 3.2;
glass_recess_depth = 1.9;

module head_outline(with_ears = true) {
    offset(r = 3) offset(delta = -3)
        union() {
            rounded_rectangle(84, 48, 13);
            if (with_ears) {
                translate([-20, 29]) rotate(8) scale([0.54, 1]) circle(r = 16);
                translate([19, 28]) rotate(-22) scale([0.56, 1]) circle(r = 15);
            }
        }
}

// Each slice shares an exact scaled contour with its neighbor.
// v3: no 0.01 mm overlap, which left hairline lips that print services flag as thin walls.
module contoured_shell(profile, with_ears = true) {
    for (i = [0:len(profile)-2]) {
        lower = profile[i];
        upper = profile[i+1];
        translate([0, 0, lower[0]])
            scale([lower[1], lower[1], 1])
                linear_extrude(height = upper[0] - lower[0],
                               scale = upper[1] / lower[1])
                    head_outline(with_ears);
    }
}

// Select "assembly", "front", "back", or "divider".
part = "assembly";
exploded = false;
housing_depth = 21.3;  // v2: +1.1 mm so the Rokland 1100 mAh battery (7.8 mm, ±tolerance) fits
divider_level = 10.8;  // v3: battery bay 9.0 mm tall (battery is 7.8)
battery_floor = 1.8;   // v2: floor 0.4 mm thinner, still 1.8 mm nylon
divider_thickness = 2.0;  // v3: thicker so the flat plate does not warp in SLS
snap_positions = [-16.5, 15];  // v3: left clip moved 1.5 mm away from the ear so the wall beside it is not thin
snap_width = 4.8;
snap_window_width = 5.8;
snap_tip = -8.4;

// Extrude a side profile along X. The tip ramp flexes inward on insertion.
module snap_tab(x, side) {
    multmatrix([[0, 0, 1, x - snap_width / 2],
                [side, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 0, 1]])
        linear_extrude(height = snap_width)
            polygon([[17.3, 0.6], [19.4, 0.6], [19.1, -1.2],
                     [19.1, -5.7], [20.45, -5.7], [20.45, -6.5],
                     [19.1, snap_tip], [17.9, snap_tip], [17.9, -1.2]]);
}

module rounded_rectangle(width, height, radius) {
    offset(r = radius)
        square([width - 2 * radius, height - 2 * radius], center = true);
}

module front() {
    difference() {
        union() {
            contoured_shell([[0, 1], [0.8, 0.996], [1.6, 0.981],
                             [2.4, 0.954], [bezel_depth, 0.92]],
                            with_ears = true);
            for (x = snap_positions, side = [-1, 1]) snap_tab(x, side);
        }
        translate([window_x, window_y, -0.1])
            linear_extrude(height = bezel_depth + 2.2)
                rounded_rectangle(window_width, window_height, 0.8);
        // LCD outer glass is offset from the active pixel area in the STEP.
        translate([-1.9475, 0, -0.1])
            linear_extrude(height = glass_recess_depth + 0.1)
                rounded_rectangle(50.5, 26.6, 0.7);
        // Continue the USB-C plug relief across the shell seam.
        translate([-46, -7, -0.1]) cube([14, 14, 1.3]);
    }
}

module back() {
    difference() {
        union() {
            difference() {
                contoured_shell([[0, 0.85], [0.8, 0.905], [1.6, 0.94],
                                 [battery_floor, 0.965], [3.8, 0.987], [6, 1.0],
                                 [12, 1.01], [17, 1.007], [housing_depth, 1]]);
                translate([-1, 0, battery_floor])
                    linear_extrude(height = housing_depth)
                        rounded_rectangle(70, 39.2, 8);  // v3: rounder corners keep the bottom corners thick
            }
            for (side = [-1, 1])
                translate([-28, side > 0 ? 18.2 : -20.0, divider_level - 1.6])
                    cube([56, 1.8, 1.6]);
        }
        // External release windows stay entirely above the battery divider.
        for (x = snap_positions, side = [-1, 1])
            translate([x - snap_window_width / 2, side > 0 ? 19.35 : -26,
                       housing_depth - 7])
                cube([snap_window_width, 6.65, 1.65]);
        // Broad relief on the USB-C end of the LILYGO reference assembly.
        translate([-46, -7, housing_depth - 5.5]) cube([14, 14, 5.6]);
        for (y = [-10, 10])
            translate([25, y - 3, housing_depth - 5.5]) cube([21, 6, 5.6]);  // v3: cut through the rim, no 0.3 mm skin
    }
}

module divider() {
    difference() {
        linear_extrude(height = divider_thickness)
            rounded_rectangle(66, 38.4, 8);  // v3: matches rounder bay corners
        translate([29, -5, -0.1]) cube([6, 10, divider_thickness + 0.2]);  // v2: bigger slot so the battery plug passes through
    }
}

if (part == "front") front();
if (part == "back") back();
if (part == "divider") divider();
if (part == "assembly") {
    color("Wheat") back();
    color("SkyBlue")
        translate([0, 0, divider_level + (exploded ? 12 : 0)]) divider();
    color("Ivory")
        translate([0, 0, housing_depth + (exploded ? 24 : 0)]) front();
}
