/**
 * Things to contain flexible LED matrix displays
 *
 * Hit F6 to render the part and then export it to STL.
 * Load in your favorite slicer and print it.
 *
 *   -- noah@hack.se, 2018
 */

/**
 * Combine with '32x8 LED Matrix grid for diffuser'
 * https://www.thingiverse.com/thing:1903744
 *
 * Additional hardware: 12x 2.6x10mm plastic screws
 */
backsideFrame32x8();

/**
 * Parts for 8x8 or 16x16 LED matrices
 *
 * Comment the above part by prefixing the module call with an asterisk
 * and then uncomment one of the parts below.  Hit F6 to render and then
 * export as STL.
 *
 */
*squareDiffuserGrid(16); // 16x16 LED matrix
*squareBacksideFrame(16);
*squareDiffuserGrid(8); // Uncomment for 8x8 LED matrix
*squareBacksideFrame(8); // 16x16 LED matrix


// Config
M2hole=1.9;
M2_3hole=2.2;
M3hole=2.7;


// Helper routine
module polyhole(d, h) {
    n = max(round(2 * d),3);
    rotate([0,0,180])
        cylinder(h = h, r = (d / 2) / cos (180 / n), $fn = n);
}


module squareDiffuserGrid(pixels=16) {
	xRows=pixels;
	yRows=pixels;
	cellSize=10;
	thickness=5;
	cylSize=6;
	gridThickness=0.8;
	componentLength=6;
	componentHeight=1.25;

	difference() {
		union() {
			// Grid
			for(x=[1:xRows-1]) {
				tmp = x != xRows/2? gridThickness: gridThickness; //*2
				translate([x*cellSize-tmp/2, 0, 0])
					cube([tmp, cellSize*yRows, thickness]);
			}
			for(y=[1:yRows-1]) {
				tmp = y != yRows/2? gridThickness: gridThickness; //*2
				translate([0, y*cellSize-tmp/2, 0])
					cube([cellSize*xRows, tmp, thickness]);
			}
			// Corners
			for(x=[0,1]) {
				for(y=[0,1]) {
					translate([-cylSize/PI+x*(xRows*cellSize+2*cylSize/PI), -cylSize/PI+y*(yRows*cellSize+2*cylSize/PI), 0])
						polyhole(d=cylSize, h=thickness);
				}
			}
			// Outer joining the corners and the grid
			for(i=[0,1]) {
				// X walls
				translate([-cylSize/2, gridThickness/2-thickness+i*(cellSize*yRows+thickness-gridThickness), 0])
					cube([cylSize+cellSize*xRows, thickness, thickness]);
				// Y walls
				translate([gridThickness/2-thickness+i*(cellSize*xRows+thickness-gridThickness), -cylSize/2, 0])
					cube([thickness, cylSize+cellSize*yRows, thickness]);
			}
		}
		// Make room for external components
		for(y=[1:yRows]) {
			for(x=[1:xRows-1]) {
				translate([x*cellSize-gridThickness,y*cellSize-cellSize/2-componentLength/2,thickness-componentHeight])
					cube([gridThickness*2,componentLength,componentHeight+.5]);
			}
		}
		// Screw holes corners
		for(x=[0,1])
			for(y=[0,1])
				translate([-cylSize/PI+x*(xRows*cellSize+2*cylSize/PI), -cylSize/PI+y*(yRows*cellSize+2*cylSize/PI), -.5])
					polyhole(d=M2_3hole, h=thickness+1);
	}
}


module squareBacksideFrame(pixels=16) {
	xRows=pixels;
	yRows=pixels;
	cellSize=10;
	thickness=5;
	cylSize=6;
	gridThickness=0.8;
	componentLength=6;
	componentHeight=1.25;
	pcbHoleDistance=36;
	usbHoleDistance=9;
	expansionBoardHoleDistanceX=45;
	expansionBoardHoleDistanceY=55;

	height=(cellSize*yRows+thickness-gridThickness);
	width=(cellSize*xRows+thickness-gridThickness);

	difference() {
		union() {
			// Corners
			for(x=[0,1]) {
				for(y=[0,1]) {
					translate([-cylSize/PI+x*(xRows*cellSize+2*cylSize/PI), -cylSize/PI+y*(yRows*cellSize+2*cylSize/PI), 0])
						polyhole(d=cylSize, h=thickness);
				}
			}
			// Outer joining the corners and the grid
			for(i=[0,1]) {
				// X walls
				translate([-cylSize/2, gridThickness/2-thickness+i*(cellSize*yRows+thickness-gridThickness), 0])
					cube([cylSize+cellSize*xRows, thickness, thickness]);
				// Y walls
				translate([gridThickness/2-thickness+i*(cellSize*xRows+thickness-gridThickness), -cylSize/2, 0])
					cube([thickness, cylSize+cellSize*yRows, thickness]);
			}
			// Stabilizator Pycom expansion board
			for(i=[-1,1]) {
				translate([0, height/2-thickness/2+i*expansionBoardHoleDistanceY/2,0])
					cube([width, thickness, thickness]);
				// Screw holes
				translate([15, height/2-i*expansionBoardHoleDistanceY/2,0])
					cylinder(d=6, h=thickness);
				translate([15, height/2-i*expansionBoardHoleDistanceY/2,0])
					cylinder(d=6, h=thickness);
				translate([15+expansionBoardHoleDistanceX, height/2-i*expansionBoardHoleDistanceY/2,0])
					cylinder(d=6, h=thickness);
				translate([15+expansionBoardHoleDistanceX, height/2-i*expansionBoardHoleDistanceY/2,0])
					cylinder(d=6, h=thickness);
			}
			// Adafruit Perma-Proto stabilizator and screw holes
			translate([0, height/2-thickness/2,0])
				cube([15+expansionBoardHoleDistanceX, thickness, thickness]);
			translate([15+expansionBoardHoleDistanceX-thickness/2, height/2-expansionBoardHoleDistanceY/2, 0])
				cube([thickness, expansionBoardHoleDistanceY, thickness]); // Join with stabilizator for Pycom exp board
			translate([15, height/2,0])
				cylinder(d=6, h=thickness);
			translate([15+pcbHoleDistance, height/2,0])
				cylinder(d=6, h=thickness);
		}
		// Screw holes corners
		for(x=[0,1])
			for(y=[0,1])
				translate([-cylSize/PI+x*(xRows*cellSize+2*cylSize/PI), -cylSize/PI+y*(yRows*cellSize+2*cylSize/PI), -.5])
					polyhole(d=M2_3hole, h=thickness+1);
		// SS-5GL micro switch screw holes
		for(y=[0,1]) {
			for(x=[-20,20]) {
				translate([x+width/2-9.5, y*height-thickness/2+gridThickness/2, -.5])
					polyhole(d=M2hole, h=thickness+1);
				translate([x+width/2, y*height-thickness/2+gridThickness/2, -.5])
					polyhole(d=M2hole, h=thickness+1);
				translate([x+width/2+9.5, y*height-thickness/2+gridThickness/2, -.5])
					polyhole(d=M2hole, h=thickness+1);
			}
		}
		for(y=[-20,20]) {
			translate([cellSize*xRows+thickness/2-gridThickness/2, y+height/2-9.5, -.5])
				polyhole(d=M2hole, h=thickness+1);
			translate([cellSize*xRows+thickness/2-gridThickness/2, y+height/2, -.5])
				polyhole(d=M2hole, h=thickness+1);
			translate([cellSize*xRows+thickness/2-gridThickness/2, y+height/2+9.5, -.5])
				polyhole(d=M2hole, h=thickness+1);
		}
		// Permaproto screw holes
		translate([15, height/2, -.5])
			polyhole(d=M3hole, h=thickness+2+1);
		translate([15+pcbHoleDistance, height/2, -.5])
			polyhole(d=M3hole, h=thickness+2+1);
		// Pycom expansion board screw holes
		for(i=[-1,1]) {
			translate([15, height/2-i*expansionBoardHoleDistanceY/2, -.5])
				polyhole(d=M3hole, h=thickness+2+1);
			translate([15, height/2-i*expansionBoardHoleDistanceY/2, -.5])
				cylinder(d=M3hole, h=thickness+2+1);
			translate([15+expansionBoardHoleDistanceX, height/2-i*expansionBoardHoleDistanceY/2, -.5])
				polyhole(d=M3hole, h=thickness+2+1);
			translate([15+expansionBoardHoleDistanceX, height/2-i*expansionBoardHoleDistanceY/2, -.5])
				polyhole(d=M3hole, h=thickness+2+1);
		}
	}
}


module backsideFrame32x8() {
	thickness=5;
	cylSize=6.25;
	screwXDistance=75;
	screwYDistance=86;
	// Extra feature: PCB mounting bars
	pcbHoleDistance=36;
	usbHoleDistance=9;
	expansionBoardHoleDistanceX=45;
	expansionBoardHoleDistanceY=55;

	difference() {
		union() {
			// 2x3 screw holes
			for(x=[0,1,2]) {
				translate([x*screwXDistance, 0, 0])
					polyhole(d=cylSize, h=thickness);
				translate([x*screwXDistance, screwYDistance, 0])
					polyhole(d=cylSize, h=thickness);
			}
			// Stabilizator
			translate([2*screwXDistance-8,-cylSize/2,0])
				rotate([0,0,45])
					cube([14,5,thickness]);
			translate([2*screwXDistance+19.5, screwYDistance, 0])
				polyhole(d=cylSize, h=thickness);

			// X beams to joins screw holes
			for(x=[0,1]) {
				translate([x*screwXDistance, -cylSize/2, 0])
					cube([screwXDistance, thickness, thickness]);
				translate([x*screwXDistance, cylSize/2-thickness+screwYDistance, 0])
					cube([screwXDistance, thickness, thickness]);
			}
			// Stabilizator
			translate([2*screwXDistance, cylSize/2-thickness+screwYDistance, 0])
				cube([19.5+cylSize/2, thickness, thickness]);

			// Y beam to join screw holes
			translate([-cylSize/2, 0, 0])
				cube([thickness, 86, thickness]);
			for(x=[1,2]) {
				translate([x*screwXDistance-thickness/2, 0, 0])
					cube([thickness, screwYDistance, thickness]);
			}

			// Extra feature: PCB mounting bars
			translate([-thickness/2+screwXDistance,0,0]) {
				// Stabilizator Adafruit perma-proto board
				translate([0, screwYDistance/2-thickness/2,0])
					cube([screwXDistance, thickness, thickness]);
				translate([15, screwYDistance/2,0])
					cylinder(d=6, h=thickness);
				translate([15+pcbHoleDistance, screwYDistance/2,0])
					cylinder(d=6, h=thickness);
				// Stabilizator Pycom expansion board
				for(i=[-1,1]) {
					translate([0, screwYDistance/2-thickness/2+i*expansionBoardHoleDistanceY/2, 0])
						cube([screwXDistance, thickness, thickness]);
					// Screw holes
					translate([15, screwYDistance/2-i*expansionBoardHoleDistanceY/2, 0])
						cylinder(d=6, h=thickness);
					translate([15, screwYDistance/2-i*expansionBoardHoleDistanceY/2, 0])
						cylinder(d=6, h=thickness);
					translate([15+expansionBoardHoleDistanceX, screwYDistance/2-i*expansionBoardHoleDistanceY/2, 0])
						cylinder(d=6, h=thickness);
					translate([15+expansionBoardHoleDistanceX, screwYDistance/2-i*expansionBoardHoleDistanceY/2, 0])
						cylinder(d=6, h=thickness);
				}
			}
		}
		// Screw holes
		for(x=[0,1,2]) {
			translate([x*screwXDistance, 0, -1])
				polyhole(d=M2_3hole, h=thickness+2);
			translate([x*screwXDistance, screwYDistance, -1])
				polyhole(d=M2_3hole, h=thickness+2);
		}
		// Stabilizator hole
		translate([2*screwXDistance+19.5,screwYDistance,-1]) polyhole(d=M2_3hole, h=thickness+2);
		// Stabilizator removal bottom side
	    translate([2*screwXDistance-cylSize/2-0.5,-cylSize/2-0.5,-1]) cube([cylSize+1,cylSize+1, thickness+2]);


		// Extra feature: PCB mounting bars
		translate([-thickness/2+screwXDistance,0,0]) {
			// Adafruit perma-proto screw holes
			translate([15, screwYDistance/2, -.5])
				polyhole(d=M3hole, h=thickness+1);
			translate([15+pcbHoleDistance, screwYDistance/2, -.5])
				polyhole(d=M3hole, h=thickness+1);
			// Pycom expansion board screw holes
			for(i=[-1,1]) {
				translate([15, screwYDistance/2-i*expansionBoardHoleDistanceY/2, -.5])
					polyhole(d=M3hole, h=thickness+2+1);
				translate([15, screwYDistance/2-i*expansionBoardHoleDistanceY/2, -.5])
					polyhole(d=M3hole, h=thickness+2+1);
				translate([15+expansionBoardHoleDistanceX, screwYDistance/2-i*expansionBoardHoleDistanceY/2, -.5])
					polyhole(d=M3hole, h=thickness+2+1);
				translate([15+expansionBoardHoleDistanceX, screwYDistance/2-i*expansionBoardHoleDistanceY/2, -.5])
					polyhole(d=M3hole, h=thickness+2+1);
			}
			// SS-5GL micro switch screw holes
			for(x=[1,3]) {
				translate([x*screwXDistance/4-9.5, cylSize/2-thickness/2+screwYDistance, -.5]) polyhole(d=M2hole, h=thickness+1);
				translate([x*screwXDistance/4, cylSize/2-thickness/2+screwYDistance, -.5]) polyhole(d=M2hole, h=thickness+1);
				translate([x*screwXDistance/4+9.5, cylSize/2-thickness/2+screwYDistance, -.5]) polyhole(d=M2hole, h=thickness+1);
				translate([x*screwXDistance/4-9.5, -cylSize/2+thickness/2, -.5]) polyhole(d=M2hole, h=thickness+1);
				translate([x*screwXDistance/4, -cylSize/2+thickness/2, -.5]) polyhole(d=M2hole, h=thickness+1);
				translate([x*screwXDistance/4+9.5, -cylSize/2+thickness/2, -.5]) polyhole(d=M2hole, h=thickness+1);
			}
		}
	}
}
