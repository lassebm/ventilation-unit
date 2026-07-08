// Ventilation-unit ESP32-S3 node — 3D-printable enclosure
// =======================================================
// Parametric enclosure for the ESP32-S3 node described in docs/HARDWARE.md:
//   - 1x ESP32-S3-DevKitC-1 (USB-host-capable; drives the controller's USB/PC link)
//   - 1x double RJ45 breakout (jacks bridged), sockets facing out a wall cutout
//
// The RJ45 jacks AND the board's two USB-C connectors all exit the SAME (front, -Y)
// wall. The breakout's two RJ45 jacks are BRIDGED (wired in parallel), so +5V / GND
// power and the front-panel + controller UART lines all ride one Ethernet cable and
// appear on both jacks — use either, or split the load across the two. The two USB-C
// connectors (native-USB host + UART/flash) stay reachable for the USB-host link and flashing.
//
// The two boards sit side by side, butting each other through one shared middle wall;
// each outer edge registers on a flat seat flange (the rounded inner corners can't seat
// a board flat). The RJ45 breakout drops into a pocket (left seat flange + shared wall as
// its right rib + a back rib), clamped by a lid tab on its jack housing — no fasteners.
// The S3 lies FLAT beside it, butted against the front wall (USB-C shells in the cutouts)
// and back wall, resting on the FLOOR on its soldered pin tails — no under-board ledge to
// foul the bottom-side pins/solder. Two stout lid tabs press its RIGID parts: a crossbar
// across both USB-C shells at the front, a bar on the RF shield can at the back (clear of
// the antenna, which sits just inside the back wall). Snap-fit lid with an L-shaped run
// of vent slots, plus four external mounting ears.
//
// Board connections (panel / controller / power) can be soldered flat to the castellated
// pads for the lowest box, OR run on dupont jumpers to vertical pin headers — the tabs
// press the board's CENTRE line (USB-C shells + RF module), clear of the edge header rows.
// For headers, raise esp_top_h to the dupont-tip height and the box grows to suit.
//
// HOW TO USE
//   1. Measure YOUR parts with calipers and update the MEASUREMENTS block. Values
//      marked  // MEASURE  are real-world dimensions to verify.
//   2. Set `part` and render (F5 preview / F6 render, export STL).
//   3. Snap fit is printer-dependent — print the lid first and tune snap_depth /
//      fit_clear.
//
// Coordinates: origin at inner-floor front-left corner. +X right, +Y back (away from
// the connector wall), +Z up. The RJ45 breakout and the S3's USB-C end sit against the
// FRONT (-Y) wall; the S3 extends back along +Y.

// ------------------------------------------------------------------
// WHAT TO RENDER
// ------------------------------------------------------------------
part = "preview";   // "preview" | "base" | "lid" | "both"
show_boards = true;     // in "preview", draw translucent board placeholders
show_connectors = true; // in "preview", also draw the USB-C connector blocks

// ------------------------------------------------------------------
// MEASUREMENTS  (edit these — see docs/HARDWARE.md for the parts)
// ------------------------------------------------------------------

// -- ESP32-S3-DevKitC-1 (lies flat, USB-C end toward the front wall) -----
esp_l      = 62.75; // MEASURE board length front->back (Y), INCLUDING the WiFi antenna
                    // overhang at the back, EXCLUDING the USB-C overhang (the PCB front
                    // edge is the datum; the shells protrude through the front wall)
esp_w      = 27.75; // MEASURE board width (along X). This default is a wider DevKitC-1
                    // clone; a genuine Espressif board is ~25.4 mm — measure yours.
esp_pcb_t  = 1.6;   // MEASURE PCB thickness
esp_comp_h = 3.2;   // MEASURE RF shield-can height above the PCB (the rear tab presses here)
esp_top_h  = 15.0;  // MEASURE tallest obstruction above the PCB — sets the box height.
                    // ~15 for a vertical pin header + mated female dupont; top_clear then
                    // adds room above for the wire bend. Soldering flat instead? Drop to
                    // esp_comp_h (~3) for a low box. The centred tabs clear the edge
                    // header rows either way.
esp_pin_h  = 2.5;   // MEASURE how far the board sits above the floor — it rests on its
                    // soldered pin tails (~2-3 mm). No tails (soldered flat)? Set ~1 mm
                    // so bottom-side SMD clears the floor. Sets the tab reach and USB-C
                    // window height (no under-board ledge to clash with the pins/solder).
esp_ant_len = 8.0;  // MEASURE keep-out at the board's BACK end (opposite the USB-C): the
                    // WROOM antenna + any overhang past the PCB edge. The back is left
                    // open across this zone and the rear tab stays off it.

// -- The board's two USB-C connectors (on the front edge, side by side) --
usb_span    = 20.0; // MEASURE outer-to-outer of the two USB-C connectors (far side of the
                    // left shell to far side of the right shell, along X)
usb_conn_w  = 9.0;  // MEASURE width of one USB-C shell (~8.9)
usb_body_h  = 3.4;  // MEASURE USB-C shell height above the PCB top face (Z)
usb_clear   = 0.7;  // clearance added around the USB openings
usb_min_div = 1.6;  // if the wall left between the two openings would be thinner than
                    // this, they merge into one window (on the DevKitC-1 they're ~2 mm
                    // apart -> one window)

// -- Double RJ45 breakout (bridged jacks) --
rj_l       = 37.4;  // MEASURE board length (along the front wall, X)
rj_w       = 28.2;  // MEASURE board depth  (whole board into the enclosure, Y)
rj_jack_d  = 18.4;  // MEASURE jack-housing depth from the front wall (Y)
rj_h       = 16.8;  // MEASURE floor to top of the jack housing (Z) — lid tab lands here
rj_win_w   = 31.9;  // MEASURE cutout width for the two jack faces (both jacks)
rj_win_h   = 12.0;  // MEASURE cutout height for the jack faces
rj_win_z   = 3.65;  // MEASURE jack-window bottom above the floor
rj_win_gap = 4.0;   // MEASURE gap between the two jacks -> centre divider so the top
                    // prints as two short bridges (0 = one wide window)

// ------------------------------------------------------------------
// ENCLOSURE / FIT PARAMETERS
// ------------------------------------------------------------------
wall_t      = 2.0;  // wall thickness
floor_h     = 2.0;  // floor thickness
lid_h       = 2.0;  // lid plate thickness
corner_r    = 3.0;  // outer corner radius (vertical edges)

fit_clear = 0.4; // slack for the lid fit and RJ45 width (loosen if the lid is tight)
top_clear = 7.5; // air gap above the tallest part, under the lid — room for the dupont
                 // cable bend above the connectors (sets the wall height)

// -- Layout across the width (front-wall zones, left -> right) -----------
// The RJ45 and the S3 butt EACH OTHER through one shared middle wall (the RJ45 pocket's
// right rib IS the S3's left locating wall). Their OUTER edges register against flat SEAT
// FLANGES proud of the side walls — the rounded inner corners can't give flat support, so
// each flange presents a straight face clear of the fillet (widening the box by
// 2*flange_proud). No cable channel — the dupont wires route over the low shared wall and
// through the empty space behind the RJ45.
flange_proud = 1.2;  // how far the seat flanges stand inboard of the side-wall inner face
                     // (> the inner corner fillet so the board edge clears it)
esp_front_gap = 0.2; // the S3 BUTTS the front wall (near-zero) so the USB-C shells seat
                     // in the cutouts; the front wall is the board's Y datum
esp_ant_clear = 0.5; // gap behind the board back edge -> case length MATCHES the board;
                     // the back wall is the +Y stop, so no back supports. The WROOM
                     // antenna then sits just inside this wall, detuning WiFi a little —
                     // raise to ~5 mm if range is poor or the antenna overhangs the PCB.
end_margin   = 3.0;  // clear space behind the RJ45 pocket (Y); the deeper S3 side (set by
                     // esp_ant_clear) usually decides the box depth

// -- RJ45 pocket (drop-in mount against the front wall) ------------------
// The board drops between the LEFT seat flange and the shared middle wall (its right
// rib), seated against the front wall, with a low back rib stopping push-in.
rj_rib_h    = 6.0;  // pocket wall height (the left flange + the shared rib rise this high)
rj_rib_t    = 1.6;  // shared-rib / back-rib wall thickness
rj_backrib_h     = 4.0;  // height of the rib behind the RJ45 board (stops push-in;
                         // kept low to clear the dupont cables in the screw terminals)
rj_back_gap      = 0.5;  // gap between the RJ45 board back edge and the back rib
rj_hold_len_frac = 0.6;  // lid hold-down tab length as a fraction of the board length
rj_hold_tip      = 4.0;  // tab thickness at the contact face (along Y)
rj_hold_root     = 9.0;  // tab thickness where it meets the lid (tapers to the tip)
rj_hold_pos_frac = 0.6;  // tab centre as a fraction of the jack-housing depth (from wall)
rj_hold_load     = -0.1; // downward reach onto the jack top (small gap; print stackup
                         // closes it to a light touch that settles the jack)

// -- S3 flat mount: shared wall + seat flanges + lid press ---------------
// The board sits on the FLOOR (on its soldered pin tails); the shared middle wall (left)
// and the right seat flange locate it in X, and the front + back walls butt its two ends
// and stop it in Y. No under-board ledge, so nothing touches the bottom-side pins/solder.
// The two lid tabs hold it down.
s3_fit   = 0.3;              // fit gap between each board edge and the wall/flange beside it
seat_lip = esp_pcb_t + 0.8;  // how far the shared wall + seat flanges rise above the PCB
                             // top, to locate the board edges
// Two stout tabs on the lid underside press the board's RIGID parts, not bare PCB: a
// crossbar across both USB-C shells at the front and a bar on the RF shield can at the
// back. Both taper root->tip and print support-free (lid top-down). They straddle the
// board's centre line, clear of the edge header rows, so vertical pin headers with dupont
// are fine (raise esp_top_h).
s3_hold       = true;
usb_hold_len  = usb_span;  // crossbar length across the two USB-C housings (X)
usb_hold_root = 8.0;       // tab thickness at the lid (Y), tapering to the tip
usb_hold_tip  = 4.0;       // tab thickness at the contact face (Y)
usb_hold_yoff = 4.5;       // contact centre, in from the board front edge (Y)
usb_hold_load = 0.0;       // reach onto the USB-C shells (0 = just touches; +ve = firmer)
mod_hold_len  = 12.0;      // bar length along the RF shield can (Y)
mod_hold_root = 8.0;       // tab thickness at the lid (X), tapering to the tip
mod_hold_tip  = 4.0;       // tab thickness at the contact face (X)
mod_hold_back = esp_ant_len + mod_hold_len/2 + 3;  // tab centre in from the board BACK
                           // edge — derived so the bar sits on the shield can, clear
                           // of the antenna keep-out (esp_ant_len)
mod_hold_load = 0.1;       // preload on the module (0.1 mm firm contact; +ve = firmer)

// Snap-fit lid
lip_h        = 6.0;  // depth the lid plug lip reaches into the enclosure
lip_t        = 1.6;  // thickness of the plug lip
snap_depth   = 0.9;  // how far the snap tooth protrudes / engages (deeper = firmer/harder to open)
snap_h       = 1.8;  // tooth height; ~2x snap_depth keeps both faces near 45 deg
snap_z       = 4.0;  // tooth center below the top rim
snap_l       = 10.0; // length of each snap tooth along the wall
snap_n_short = 2;    // teeth per SHORT wall (front/back)
snap_n_long  = 2;    // teeth per LONG wall (sides)

// Ventilation — one run of thin, evenly-spaced Y-running slots in the LID, filling the
// width. Every slot has a front band (behind the front tabs, ending short of the rear
// module tab); the LEFT-HALF slots also extend back to form the L's foot (over the free
// space behind the RJ45), split off the band by a crossbar. The half split keeps the foot
// symmetric about the lid centreline. Set lid_vents=false to seal it.
lid_vents = true;
vent_w    = 1.6;  // slot width (thin), same for every slot
vent_gap  = 3.0;  // gap between slots, and crossbar width splitting the long slots
vent_edge = 4.0;  // margin from the side walls (the slot run fills between these)

// Wall-mount ears — flat flanges at the base with a screw hole, for flush
// surface mounting. Two per long side (+/-X), inset from the ends (4 total).
mount_ears    = true;
mount_ext     = 7.0;   // how far the ear reaches out past the wall (X)
mount_ear_w   = 12.0;  // ear width along the wall (Y)
mount_ear_h   = 3.0;   // ear/flange thickness (Z)
mount_hole_d  = 3.4;   // screw clearance hole (M3 -> 3.4)
mount_inset   = 13.0;  // ear centre distance in from each end (Y)
mount_gusset  = 7.0;   // gusset height up the wall for strength (0 = none)

// Lid grip — a tiny channel in the UNDERSIDE of the connector-end edge, running
// inward from the outer edge, so a nail slides under the lip and catches to lift.
lid_grip = true;
grip_w   = 8.0;   // channel width along the edge (X)
grip_l   = wall_t + fit_clear/2;  // reach in from the outer edge (Y) — ends right
                  // against the lip's outer face, without running over/past the lip
grip_d   = 0.7;   // channel depth up into the lid underside (Z)

$fn = 48;

// ==================================================================
// DERIVED LAYOUT
// ==================================================================
// Widthwise, left -> right, the boards share a middle wall and register on seat flanges:
//   |wall|flange| RJ45 board | SHARED wall | S3 board |flange|wall|
// The seat flanges (proud of the side walls) are the outer locating faces; the shared
// wall is the RJ45 pocket's right rib AND the S3's left locating wall.
shared_t  = rj_rib_t;                        // shared middle wall = the RJ45 pocket's right rib
rj_open_w = rj_l + fit_clear;                // RJ45 pocket opening (board + slack)
rj_open_l = wall_t + flange_proud;           // pocket opening left = LEFT seat flange face
shared_l  = rj_open_l + rj_open_w;           // shared wall left face (RJ45 board right edge)
esp_x0    = shared_l + shared_t + s3_fit;    // S3 PCB left edge

// ...+2*flange_proud: the boards butt the seat flanges, not the walls (S3 right edge
// sits s3_fit off the RIGHT flange, whose face is flange_proud in from the wall).
inner_x = 2*flange_proud + rj_open_w + shared_t + s3_fit + esp_w + s3_fit;
inner_y = max(rj_w + rj_back_gap + rj_rib_t + end_margin, esp_front_gap + esp_l + esp_ant_clear);
inner_z = max(rj_h, esp_pin_h + esp_pcb_t + esp_top_h) + top_clear;

// Outer envelope
out_x = inner_x + 2*wall_t;
out_y = inner_y + 2*wall_t;
out_z = floor_h + inner_z;

// Absolute X centres.
rj_cx  = rj_open_l + rj_open_w/2;            // RJ45 windows/pocket centre
esp_cx = esp_x0 + esp_w/2;                   // == USB-C cutouts centre
esp_y0 = wall_t + esp_front_gap;             // S3 PCB front edge
esp_cy = esp_y0 + esp_l/2;

// USB-C window band, above the floor-mounted board top.
usb_win_z = floor_h + esp_pin_h + esp_pcb_t - usb_clear;  // opening bottom
usb_win_h = usb_body_h + 2*usb_clear;                     // opening height

// ==================================================================
// HELPERS
// ==================================================================
module rrect(x, y, r) {
  hull() {
    translate([r, r])         circle(r);
    translate([x - r, r])     circle(r);
    translate([r, y - r])     circle(r);
    translate([x - r, y - r]) circle(r);
  }
}

// N positions evenly spread along a wall of the given length (interior spacing).
function spread(n, len) = [for (i = [0:n-1]) len*(i + 1)/(n + 1)];

// ==================================================================
// BASE
// ==================================================================
module base() {
  difference() {
    linear_extrude(out_z) rrect(out_x, out_y, corner_r);   // outer shell

    // Inner cavity (open top)
    translate([wall_t, wall_t, floor_h])
      linear_extrude(out_z)
        rrect(inner_x, inner_y, max(0.1, corner_r - wall_t));

    // RJ45 jack windows in the FRONT (-Y) wall, centred on the RJ45 zone. A centre
    // divider (rj_win_gap) splits it into two openings so the top prints as two short
    // bridges.
    rj_win_half = (rj_win_w - rj_win_gap) / 2;
    for (x0 = [rj_cx - rj_win_gap/2 - rj_win_half, rj_cx + rj_win_gap/2])
      translate([x0, -0.1, floor_h + rj_win_z])
        cube([rj_win_half, wall_t + 0.2, rj_win_h]);

    // USB-C windows in the FRONT (-Y) wall, centred on the S3 zone. Each opening is a
    // shell + clearance; if the wall left between them is too thin to print, they merge
    // into one window.
    usb_div = usb_span - 2*usb_conn_w - 2*usb_clear;   // wall left between the two openings
    if (usb_div >= usb_min_div)
      for (x0 = [esp_cx - usb_span/2 - usb_clear, esp_cx + usb_span/2 - usb_conn_w - usb_clear])
        translate([x0, -0.1, usb_win_z])
          cube([usb_conn_w + 2*usb_clear, wall_t + 0.2, usb_win_h]);
    else
      translate([esp_cx - usb_span/2 - usb_clear, -0.1, usb_win_z])
        cube([usb_span + 2*usb_clear, wall_t + 0.2, usb_win_h]);

    // Snap notches (receive the lid teeth)
    snap_grooves();
  }

  // RJ45 pocket: the board drops in between the LEFT seat flange and the SHARED wall
  // (its right rib, drawn by shared_wall), with a back rib joining them. It seats against
  // the front wall; the lid tab clamps it. Clear gap = rj_l + fit_clear.
  translate([wall_t, wall_t + rj_w + rj_back_gap, floor_h])   // back rib: left wall -> shared wall
    cube([(shared_l + shared_t) - wall_t, rj_rib_t, rj_backrib_h]);

  // Shared middle wall + the two outer seat flanges
  shared_wall();
  if (flange_proud > 0) seat_flanges();

  // Wall-mount ears (external flanges at the base)
  if (mount_ears)
    for (dir = [-1, 1])                                   // left / right wall
      for (yc = [wall_t + mount_inset, out_y - wall_t - mount_inset])
        mount_ear(dir, (dir < 0) ? 0 : out_x, yc);
}

// Shared middle wall: the RJ45 pocket's right rib AND the S3's left locating wall. Runs the
// FULL interior depth, fused into the front and back walls (braced at both ends, not a free
// fin), as tall as the taller of its two duties (RJ45 pocket wall vs. rising past the S3
// PCB to locate its edge).
module shared_wall() {
  s3_edge_h = esp_pin_h + esp_pcb_t + seat_lip;
  h         = max(s3_edge_h, rj_rib_h);
  translate([shared_l, wall_t, floor_h]) cube([shared_t, inner_y, h]);
}

// Seat flanges: flat pads standing flange_proud in from the (rounded) side walls, so the
// outer board edges register on a STRAIGHT vertical face clear of the corner fillets. Left
// flange = the RJ45 pocket's left wall (over the RJ45 depth); right flange = the S3's right
// locating wall (full interior depth).
module seat_flanges() {
  s3_edge_h = esp_pin_h + esp_pcb_t + seat_lip;
  translate([wall_t, wall_t, floor_h])                          // LEFT (RJ45 left edge)
    cube([flange_proud, rj_w + rj_rib_t, rj_rib_h]);
  translate([wall_t + inner_x - flange_proud, wall_t, floor_h]) // RIGHT (S3 right edge)
    cube([flange_proud, inner_y, s3_edge_h]);
}

// One flush-mount ear: a flange fused to the OUTER wall face reaching out to a
// rounded end with a screw hole, plus a gusset ramping down the wall for strength.
module mount_ear(dir, x_face, yc) {
  r     = mount_ear_w/2;
  bite  = 0.5;                            // slight overlap into the wall to fuse
  x_in  = x_face - dir*bite;              // flat inner edge, just inside the wall
  x_out = x_face + dir*mount_ext;         // screw-hole centre, outboard
  difference() {
    hull() {
      translate([x_in, yc - r, 0]) cube([0.01, mount_ear_w, mount_ear_h]);  // flat inner edge
      translate([x_out, yc, 0])    cylinder(r = r, h = mount_ear_h);        // rounded outer end
    }
    translate([x_out, yc, -0.1]) cylinder(d = mount_hole_d, h = mount_ear_h + 0.2);
  }
  if (mount_gusset > 0)                    // brace ramping down the outside of the wall
    hull() {
      translate([x_in, yc - r, 0])                cube([0.01, mount_ear_w, mount_gusset]);
      translate([x_face + dir*mount_ext*0.6, yc - r, 0]) cube([0.01, mount_ear_w, mount_ear_h]);
    }
}

module snap_grooves() {
  z = out_z - snap_z;
  // short walls (front/back): slot runs snap_l along X, through the wall (Y)
  for (px = spread(snap_n_short, out_x))
    for (cy = [wall_t/2, out_y - wall_t/2])
      translate([px - snap_l/2, cy - wall_t, z - snap_h/2])
        cube([snap_l, wall_t*2, snap_h]);
  // long walls (sides): slot runs snap_l along Y, through the wall (X)
  for (py = spread(snap_n_long, out_y))
    for (cx = [wall_t/2, out_x - wall_t/2])
      translate([cx - wall_t, py - snap_l/2, z - snap_h/2])
        cube([wall_t*2, snap_l, snap_h]);
}

// ==================================================================
// LID  (snap-fit plug lid)
// ==================================================================
module lid() {
  difference() {
    union() {
      linear_extrude(lid_h) rrect(out_x, out_y, corner_r);   // top plate

      translate([0, 0, -lip_h])                              // plug lip
        linear_extrude(lip_h)
          difference() {
            offset(delta = -(wall_t + fit_clear/2)) rrect(out_x, out_y, corner_r);
            offset(delta = -(wall_t + fit_clear/2 + lip_t)) rrect(out_x, out_y, corner_r);
          }

      lid_snaps();
      rj_hold_tab();
      if (s3_hold) { s3_usb_tab(); s3_mod_tab(); }
    }
    // Vent grille through the plate, over the S3 board
    if (lid_vents) lid_vent_cut();
    // Nail groove under the connector-end edge, to lift the lid off
    if (lid_grip) lid_grip_cut();
  }
}

// Tiny channel in the UNDERSIDE at the connector-end (front, -Y) edge: runs inward from
// the outer edge for a nail to catch and lift the lid, up to the lip (grip_l). The inner
// end is a rounded fillet (radius = depth), not a square corner, so no stress riser sits
// on a layer line to peel under the prying force.
module lid_grip_cut() {
  x0 = out_x/2 - grip_w/2;
  r  = grip_d;                                   // fillet radius on the inner end
  hull() {
    translate([x0, -0.5,        -0.05])  cube([grip_w, 0.01, 0.01]);  // front, at underside
    translate([x0, -0.5,        grip_d]) cube([grip_w, 0.01, 0.01]);  // front, top of groove
    translate([x0, grip_l,      -0.05])  cube([grip_w, 0.01, 0.01]);  // inner, at underside
    translate([x0, grip_l - r,  grip_d - r]) rotate([0, 90, 0])
      cylinder(r = r, h = grip_w, $fn = 32);                          // rounded inner-top corner
  }
}

// RJ45 hold-down tab: presses the top of the jack housing when the lid is closed. Lid-local
// z=0 is the plate underside (== top of the walls when installed); the tab reaches down to
// the housing top (rj_h) plus a small preload. Tapered — wide root at the lid, narrowing to
// the contact face.
module rj_hold_tab() {
  gap  = inner_z - rj_h;
  tabx = rj_l * rj_hold_len_frac;
  cx   = rj_cx;
  cy   = wall_t + rj_jack_d*rj_hold_pos_frac;
  hull() {
    translate([cx - tabx/2, cy - rj_hold_root/2, -0.5])       // root at the lid
      cube([tabx, rj_hold_root, 0.5]);
    translate([cx - tabx/2, cy - rj_hold_tip/2,               // contact face
               -(gap + rj_hold_load)])
      cube([tabx, rj_hold_tip, 0.5]);
  }
}

// S3 front hold-down: a crossbar across BOTH USB-C housings, reaching down from the lid
// to the shell tops. Runs its length along X and tapers root->tip along Y, so it braces
// the weak axis and prints support-free (lid top-down, narrow contact face upward).
module s3_usb_tab() {
  gap = inner_z - (esp_pin_h + esp_pcb_t + usb_body_h);   // lid underside -> shell top
  cx  = esp_cx;
  cy  = esp_y0 + usb_hold_yoff;
  hull() {
    translate([cx - usb_hold_len/2, cy - usb_hold_root/2, -0.5])      // root at the lid
      cube([usb_hold_len, usb_hold_root, 0.5]);
    translate([cx - usb_hold_len/2, cy - usb_hold_tip/2,             // contact face
               -(gap + usb_hold_load)])
      cube([usb_hold_len, usb_hold_tip, 0.5]);
  }
}

// S3 rear hold-down: a bar along the RF shield can, reaching down to its top. Runs its
// length along Y (over the can) and tapers root->tip along X.
module s3_mod_tab() {
  gap = inner_z - (esp_pin_h + esp_pcb_t + esp_comp_h);   // lid underside -> shield-can top
  cx  = esp_cx;
  cy  = esp_y0 + esp_l - mod_hold_back;
  hull() {
    translate([cx - mod_hold_root/2, cy - mod_hold_len/2, -0.5])      // root at the lid
      cube([mod_hold_root, mod_hold_len, 0.5]);
    translate([cx - mod_hold_tip/2, cy - mod_hold_len/2,            // contact face
               -(gap + mod_hold_load)])
      cube([mod_hold_tip, mod_hold_len, 0.5]);
  }
}

// L-shaped slot run: thin Y-running slots across the width, EVENLY spaced. Every slot has
// a band segment (behind the front tabs, ending short of the rear module tab); the LEFT
// HALF also extend back to form the L's foot (over the free space behind the RJ45), split
// off the band by a crossbar for stiffness. The split keeps the foot symmetric about the
// lid centreline.
module lid_vent_cut() {
  yFront  = wall_t + rj_jack_d*rj_hold_pos_frac + rj_hold_root/2 + 2;  // behind the front tabs
  yBand   = esp_y0 + esp_l - mod_hold_back - mod_hold_len/2 - 2;       // band ends before the module tab
  yBack   = wall_t + inner_y - 4;                                      // foot extension runs to the back
  foot_x  = out_x/2;                                                   // foot = the left-half slots
  pitch   = vent_w + vent_gap;
  x_lo    = wall_t + vent_edge;
  x_hi    = wall_t + inner_x - vent_edge;
  n       = floor((x_hi - x_lo + vent_gap) / pitch);
  x0      = x_lo + ((x_hi - x_lo) - (n*pitch - vent_gap)) / 2;
  for (i = [0:n-1]) {
    cx = x0 + i*pitch;
    translate([cx, yFront, -0.1]) cube([vent_w, yBand - yFront, lid_h + 0.2]);   // band: every slot (even)
    if (cx < foot_x)                                                             // foot: left-half slots
      translate([cx, yBand + vent_gap, -0.1]) cube([vent_w, yBack - yBand - vent_gap, lid_h + 0.2]);
  }
}

module lid_snaps() {
  z = -snap_z;
  off = wall_t + fit_clear/2;                 // lip outer face, from each edge
  for (px = spread(snap_n_short, out_x)) {
    translate([px, off,         z])                   snap_bump();  // front (-Y)
    translate([px, out_y - off, z]) rotate([0, 0, 180]) snap_bump(); // back  (+Y)
  }
  for (py = spread(snap_n_long, out_y)) {
    translate([off,         py, z]) rotate([0, 0, -90]) snap_bump(); // left  (-X)
    translate([out_x - off, py, z]) rotate([0, 0,  90]) snap_bump(); // right (+X)
  }
}

module snap_bump() {
  // Symmetric tooth pointing -Y: base spans the full height at the lip and tapers
  // to a tip at mid-height, so BOTH the lead-in and the retention face slope
  // (~45 deg at snap_h = 2*snap_depth) and print support-free with the lid top-down.
  hull() {
    translate([-snap_l/2, 0, -snap_h/2]) cube([snap_l, 0.01, snap_h]);      // base at lip
    translate([-snap_l/2, -snap_depth, -0.005]) cube([snap_l, 0.01, 0.01]); // tip, mid-height
  }
}

// ==================================================================
// PREVIEW ASSEMBLY
// ==================================================================
module boards_preview() {
  // RJ45 breakout (in its pocket against the front wall): tall jack housing at
  // the front, board + rear screw terminals extending back to rj_w.
  color("SteelBlue", 0.5)
    translate([rj_cx - rj_l/2, wall_t, floor_h]) {
      cube([rj_l, rj_w, 3]);              // board + low rear components
      cube([rj_l, rj_jack_d, rj_h]);      // jack housing (front, tall)
    }

  // ESP32-S3-DevKitC-1, lying flat on the floor (resting on its soldered pin tails),
  // front edge butted to the front wall.
  can_len = 18;
  translate([esp_x0, esp_y0, floor_h + esp_pin_h]) {
    color("ForestGreen", 0.6) cube([esp_w, esp_l, esp_pcb_t]);          // PCB
    color("Silver", 0.7)                                                 // RF shield can
      translate([esp_w/2 - 9, esp_l - esp_ant_len - can_len, esp_pcb_t])
        cube([18, can_len, esp_comp_h]);
    color("Peru", 0.8)                                                   // WROOM antenna keep-out
      translate([esp_w/2 - 8, esp_l - esp_ant_len, esp_pcb_t]) cube([16, esp_ant_len, 1.0]);
    if (show_connectors)                                                 // two USB-C shells (front)
      for (x0 = [esp_w/2 - usb_span/2, esp_w/2 + usb_span/2 - usb_conn_w])
        color("DimGray", 0.7)
          translate([x0, -esp_front_gap - 1, esp_pcb_t])
            cube([usb_conn_w, 8, usb_body_h]);
  }
}

// ==================================================================
// DISPATCH
// ==================================================================
if (part == "base") base();
else if (part == "lid") lid();
else if (part == "both") { base(); translate([out_x + 10, 0, 0]) lid(); }
else {
  base();
  if (show_boards) boards_preview();
  // Lid stood on its LONG edge beside the base, underside toward the base.
  color("gainsboro")
    translate([out_x + 35, 0, out_x]) rotate([0, 90, 0]) lid();
}
