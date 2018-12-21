/**
 * Combine with '32x8 LED Matrix grid for diffuser'
 * https://www.thingiverse.com/thing:1903744
 *
 * 12x 2.6x10mm plastic screws
 *
 *   -- noah@hack.se, 2018
 *
 */


module polyhole(d, h) {
    n = max(round(2 * d),3);
    rotate([0,0,180])
        cylinder(h = h, r = (d / 2) / cos (180 / n), $fn = n);
}

thickness=5;
cylSize=6.25;
screwXDistance=75;
screwYDistance=86;

difference() {
    union() {
        // 2x3 screw holes
        for(x=[0,1,2]) {
            translate([x*screwXDistance,0,0]) polyhole(d=cylSize, h=thickness);
            translate([x*screwXDistance,screwYDistance,0]) polyhole(d=cylSize, h=thickness);
        }
        // Stabilizator
        translate([2*screwXDistance-8,-cylSize/2,0]) rotate([0,0,45])cube([14,5,thickness]); 
        translate([2*screwXDistance+19.5,screwYDistance,0]) polyhole(d=cylSize, h=thickness);

        // X beams to joins screw holes
        for(x=[0,1]) {
            translate([x*screwXDistance,-cylSize/2,0]) cube([screwXDistance,thickness, thickness]);
            translate([x*screwXDistance,cylSize/2-thickness+screwYDistance,0]) cube([screwXDistance,thickness, thickness]);
        }
        // Stabilizator
        translate([2*screwXDistance,cylSize/2-thickness+screwYDistance,0]) cube([19.5+cylSize/2,thickness, thickness]);

        // Y beam to join screw holes
        translate([-cylSize/2,0,0]) cube([thickness, 86, thickness]);
        for(x=[1,2])
        translate([x*screwXDistance-thickness/2, 0, 0]) cube([thickness, screwYDistance, thickness]);
    }
    // Screw holes
    for(x=[0,1,2]) {
        translate([x*screwXDistance,0,-1]) polyhole(d=2.2, h=thickness+2);
        translate([x*screwXDistance,screwYDistance,-1]) polyhole(d=2.2, h=thickness+2);
    }
    // Stabilizator hole
    translate([2*screwXDistance+19.5,screwYDistance,-1]) polyhole(d=2.2, h=thickness+2);
    // Stabilizator removal bottom side
#    translate([2*screwXDistance-cylSize/2-0.5,-cylSize/2-0.5,-1]) cube([cylSize+1,cylSize+1, thickness+2]);
}
