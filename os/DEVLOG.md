# DruidOS Development Log

## 2026-10-20 - Everything in English

The repository's rule (`CODING.md`) is that everything in it is English;
`os/` had drifted. The Settings app was written in Portuguese (its folder,
`ajustes`, its module, its services, its tabs, its fields, its messages),
and so were the screen's help line, the F1 menu and the window's offers
count, the test pages of `hive-screen` and the Hive lab, two VM tapes,
this log, `STATUS.md` and `docs/HIVE-STACK.md`. Nobody asked for that: the
person asking writes in Portuguese, which is no reason for the repository
to.

**Renamed.** `apps/ajustes` is `apps/settings` (`hive settings`); its
module `leitura.py` is `machine.py`, its services `settings.machine`,
`settings.network`, `settings.keyboard`, `settings.screen`, `settings.hive`
and `settings.ask`; the tabs are Machine, Network, Keyboard, Screen, Hive;
the buttons say "Ask the Hive"; the network form's source is `dhcp` or
`static`. The VM tapes are `settings.jsonl`, `settings-hostname.jsonl` and
`settings-network.jsonl`; `tests/apps/test_ajustes.py` is
`tests/apps/test_settings.py`.

**The screen says it in English**: "type · arrows · Enter sends · Esc
closes" and the rest of the help line, "The Hive's offers" over "Enter
approves · Del dismisses · Esc closes" in the F1 menu, "nothing for now",
"F1 · 2 offers". The reference frames in `crates/hive-screen/tests/screens/`
were drawn again (`UPDATE_SCREENS=1`). The test pages are a Tasks page with
English fields; the Brazilian keyboard's tape types "façade piñata" (ç from
its own key, ñ from the dead ~ and n) where it typed a Portuguese word.

**Translated**: this log, whole (the entries below say Settings where they
said Ajustes), `STATUS.md` and `docs/HIVE-STACK.md`. The rule is now
written in this folder's `CLAUDE.md` too ("Language", under the coding
conventions).

## 2026-10-20 - Settings, network: the only setting with root, and the only dangerous one

Slice 5d. The network completes the basics Daniel asked for (name, network,
keyboard) by the same path as the others: request, offer, Enter, actuator.
Two things set it apart, and both are in the design.

**It is dangerous.** `SetNetwork { interface, dhcp, address, gateway, dns }`
is `is_dangerous`: a wrong address takes the machine off the network. On the
screen, the first Enter arms the offer and the second approves it (leaving it
disarms it); on the dashboard, a confirmation. The value is checked four times,
always against the same yardstick (`is_valid_network`: interface name, IPv4
with prefix, IPv4 gateway, up to four DNS servers): in `hive request`, on the
page, in the whitelist and again in the root step.

**It needs root, and the actuator does not have it.** netplan's D-Bus refuses
anyone who is not root, and giving root to the actuator would break the house
rule. So the actuator writes the setting (JSON in `/var/lib/hive/settings/network`),
empties `network.result` and starts `quantum-network-apply.service`, a root
oneshot that the manage-units polkit rule already lets it start; the script
(`scripts/network-apply`, python3 with only the standard library) keeps the
previous `/etc/netplan/60-hive.yaml` as `60-hive.yaml.before`, writes the new
one for that interface only (mode 600; cloud-init's file for the same
interface stays underneath, netplan merges them), applies it and waits up to
20 s for the interface to have the address (the static one, or any one by
DHCP). If it does not come, the previous file comes back and is applied again:
a wrong address never leaves the machine off the network waiting for a hand.
The result goes to `network.result` ("ok: enp0s1 has 10.0.2.20/24" or
"failed: ..."), and that is what the actuator answers with.

**On the page.** The Network tab gets the form (interface, source dhcp/static,
address/prefix, gateway, DNS), which starts from what the first interface
has; `settings.ask('set-network', ...)` builds the command's words and the
flash warns that it takes two Enters. On the command line: `hive request set-network
IFACE dhcp` or `IFACE ADDR/PREFIX [via GATEWAY] [dns A,B]`.

**Proof.** Hive lab: `request-network.jsonl` (static and then DHCP, each one
an offer on behalf of druid, confirmed, and `SetNetwork` reaches the actuator).
Unit tests: validation, description, whitelist, CLI, `ask` with the wrong
fields named before asking, the form on the screen with `ask` swapped.
VM: `settings-network.jsonl` asks for 10.0.2.20/24 via 10.0.2.2 dns 10.0.2.3,
arms it with one Enter (the actuator sees nothing), approves it with the
second, and the real `ip addr` has the static address and loses the lease, the
default route goes through 10.0.2.2, the netplan file is there with mode 600;
then it goes back to DHCP, with the `.before` kept and the lease back.

**What stays out, on purpose.** IPv6, more than one interface per request,
Wi-Fi (no card in the lab; it is another setting, with a secret) and writing
`/etc/netplan` by hand instead of `netplan apply`.

## 2026-10-20 - Settings, changing: the page asks, the Hive offers, Enter approves, the actuator executes

Slice 5c, by path A of the proposal (the recommended one; Daniel named no
other): nothing that changes the system goes outside the Hive's door.

**The request.** A new message on the user socket,
`HiveMessage::UserRequest { action, reason }`, which any local user can send
and which only accepts the settings (`Action::is_a_setting`: `SetHostname`,
`SetKeyboard`, `SetScreenLevel`; any other action is refused with a warning in
the log). The cortex turns it into an offer on behalf of whoever asked
(`offer_request`: a notification of type `request`, title "druid asks: name
the machine forge", fields `user`, `action`, `what`, `count`), stored like any
suggestion; whoever is at the console approves it with Enter (or F1 over a
page) and the actuator executes it through the whitelist.

**The `hive` command.** The Hive's protocol is bincode, which Python does not
speak; instead of teaching it, the shell launcher became a Rust binary
(`crates/hive-cli`): `hive settings` opens the app, `hive apps` lists them,
`hive request set-hostname NAME | set-keyboard LAYOUT [MODEL] |
set-screen-level auto|plain|effects|fine [--reason TEXT]` sends the request.
The app's `settings.ask` service runs that command through the third door,
`ask`, the only one that changes anything, and only by asking; the "Ask the
Hive" buttons on the Machine, Keyboard and Screen tabs call `q:` actions that
invoke it and show the answer in the flash.

**The actions, in the actuator.** `set-hostname` runs `hostnamectl set-hostname`
over D-Bus with polkit's permission for `_hive-act`
(`61-druidos-hive-settings.rules`: only the name, nothing else of hostnamed).
The keyboard was going through `localectl set-x11-keymap`, but the VM showed
that Ubuntu's localed refuses ("Setting X11 and console keymaps is not
supported in Debian"); so `set-keyboard` and `set-screen-level` do not need
root: they write or delete `keyboard` (`br abnt2`) and `screen-level` in
`/var/lib/hive/settings`, the actuator's `StateDirectory`, readable by all,
and `/etc/default/keyboard` stays as the installer left it. The whitelist gets
the three permits (`qh:allow action=` in `hive.q`, two per minute) and refuses
a value that hostnamectl would not accept or the screen would not read (host
label; us/br layouts with their models; level 0–2).

**The screen follows live.** Twice a second the daemon rereads the keyboard
(`Layout::detect`: the environment, then the Hive's setting, then the system
file; `Keyboards::set_layout`, without restarting) and the level file (pins
or releases the chooser; `HIVE_SCREEN_LEVEL` in the environment still takes
precedence), and reports it in the log and in the `status` it sends to the
page's runtime. A request is an event of its own in the scene
(`qs:on event="request"`: "{user} asks: {what}") and enters the offers panel
like any offer.

**Proof.** Hive lab: `request-hostname.jsonl` (the request becomes an offer on
behalf of druid, nothing runs until it is approved, the actuator receives
`SetHostname`; a `RestartService` request never becomes an offer). Unit tests:
validation and description of the actions, the whitelist closed and open, the
user socket, the words of `hive request`. `tests/apps/test_settings.py`:
`ask` with the `ask` door swapped and the click on "Ask the Hive" on the screen.
VM: `settings-hostname.jsonl` asks for the name, the keyboard and the level as
druid, approves each one with Enter on the real keyboard, and `hostname` and
the two setting files change (`/etc/default/keyboard` does not), with the
screen rereading the keyboard ("keyboard layout br (ABNT2)") and the level
("level 0 pinned by the Hive's settings") without restarting. A new offer takes
the focus when the previous one has already been answered: Enter answers what
is waiting.

**What remains.** The network (5d, `set-network`, dangerous, double Enter,
previous file kept); the text console's keyboard (tty2), which belongs to the
system's `console-setup` and not to the Hive; a limit on pending requests per
user.

## 2026-10-20 - Settings, reading: the app, and the Quantum runtime inside the system

Slice 5b. The app Daniel asked for ("an admin screen with the PC's name,
network, keyboard, everything on screen") reading the real machine, and what
was missing for it to run.

**What was missing.** Neither the lab's VM nor the ISO had Quantum's Python
runtime: `quantum pixel` had only been proven by a raw socket client. Now the
runtime goes with the Hive: the dependencies (flask, yaml, sqlparse, requests,
bcrypt) as Ubuntu packages in the VM's base (`PACKAGES`, `BASE_VERSION` 7)
and in the ISO's image; the repository's `quantum/` package copied to
`/usr/lib/python3/dist-packages` (the lab's `stage()` puts it next to the
binaries and a per-file hash decides what to reinstall); `/usr/bin/quantum`
and `/usr/bin/hive` (`hive settings` opens the app on the screen as the user
who called it; `hive apps` lists them; `/usr/share/quantum-os/apps`). Textual
stays out (Ubuntu's is too old): on the machine the app runs on the screen and
in the browser, not in the console. The ISO is still not validated here.

**The app (`apps/settings`).** Five tabs of a `ui:tabpanel`: Machine (name,
system, kernel, uptime, cores, memory, disk), Network (each interface with
address, state and DHCP/static source; gateway; DNS), Keyboard (the system's
layout and what the screen reads), Screen (level, choice, cores, frame cost,
motion) and Hive (the daemons and their state, what the whitelist allows).
Each tab is a service of `machine.py`, stdlib only, which reads what anyone
can read (`/proc`, `/etc/default/keyboard`, `/etc/hive/whitelist.toml`,
`ip -j addr`, `ip -j route`, `resolvectl`, `systemctl is-active`) through two
doors, `run` and `read`, which the test swaps for a canned machine; nothing
raises an error: without `ip` or without the screen it reads "not read". The
Hive tab's "latest offers" were left out: the journal is not for the ordinary
user.

**The screen's status.** The proposal said `{"op":"status"}` requested by the
page; the socket accepts only one client and the service runs in another
thread of the same process, so the daemon pushes: `{"event":"status",...}` on
connecting and at every change (level, pinned or not, cores, motion, keyboard,
frame cost, scene), `Runtime::status`; the client waits half a second for it
before the first page and keeps it in `screen_status()`.

**What the VM showed.** The first run failed: the app's server opened
`logs/quantum.log` inside `/usr/share`, which does not belong to the user. The
installed app does not write a log to a file (`logging: file: false`) and the
runtime now warns and carries on with the console only when the log directory
is not writable. The `settings.jsonl` tape then passed (121 s): `hive settings`
as druid, "page: Settings" in the journal, the view the app's server answers
with `name: quantum-lab`, `cores: 4`, `level:` and `hive-screen: active`,
arrows through the tabs on the real keyboard, Esc.

**Proof outside the VM.** `tests/apps/test_settings.py`: the services against
the canned machine, and the page in the browser, in the console and on the
screen (the parity test's drivers), where the Screen tab says
`level: effects (1)`.

**Next.** The change through the Hive (5c): the page asks, the cortex offers,
Enter on the screen approves, the actuator executes through the whitelist.

## 2026-10-20 - The F1 menu and the window's button on the bar

The fourth step of slice 5: the Hive's offers arrive on top of whatever is on
the screen, and the bottom bar starts to be a taskbar.

**The menu.** F1 opens a drawer in the bottom-left corner, in the look of the
windows (`window::draw_menu`: a frame with a shadow, a honey title bar "The
Hive's offers", one line per offer with the focused one raised and in honey,
a status bar "Enter approves · Del dismisses · Esc closes"); empty, it says
"nothing for now". While it is out, the keys are its own: arrows, Enter
approves (twice for the dangerous one), Del dismisses, Esc closes and the page
listens to the keyboard again. `approve()` and `dismiss()` moved out of
`key()` to serve the scene's panel and the menu. Without a page, F1 opens the
same menu over the comb.

**The drawer.** It slides in from the left in 8 ticks (`Quad`/`Out`) and
pushes the comb 4 px to the right while it is out (the bars stay); it closes
the same way. In `plain` it opens and closes at once. The observation says
`menu` (`open`, `t`, `ticks`), `until still` waits for the drawer to stop and
`until menu` waits for the menu to be open or closed.

**The bar.** The window's status bar shows "F1 · N offers" in honey on the
right when there are offers waiting, and the help is cut at a separator
(`cut_at_separator`), never in the middle of a word. The scene's bottom bar
shows the open page as a raised button on the left, like a taskbar;
`screen.q` says `{offers} offers · F1` on the right.

**Proof.** `tests/play.rs` gets the test of the menu over the page (offers
arrive with the page open, F1 halfway, approval of the dangerous one with two
Enters, Del, Esc giving the keyboard back to the page, the empty menu over the
comb, `plain` at once) and four frames: `window-offers.png`,
`menu-drawer.png`, `menu.png`, `menu-empty.png`; the other frames were redone
for the bar's new text.

**What remains.** Several windows on the bar (Alt+1..9, F2) wait for more than
one client on the socket; the installed apps in the menu wait for the Settings
app (5b), which is what registers an app; the bee that brings the offer and
the zoom into the cell are the next motions.

## 2026-10-20 - The comb gets bars, panels and cells in relief

The third step of slice 5: the scene around the window takes on the same look
as the window. The proposal's sketch `cena.png` became a reference frame.

**In the language (`qs:`).** A new tag, `qs:bar side="top|bottom"`, with
`title=` (in the highlight color), `left=` and `right=`; the texts accept the
screen's own fields, `{clock}`, `{level}`, `{cores}`, `{host}` and `{offers}`,
and refuse the event fields (those go in a `qs:say`). `qs:offers` and
`qs:notices` get `title=`: with a title they become panels with a raised
frame, a 3 px shadow and a title bar, as tall as their lines. One bar per
side; the schema, the model, the compiler, the reference
(`docs/targets/screen.md`, with the section "The look of the scene" and the
table of fields) and the feature's dataset follow along.

**In the daemon.** `world.rs` draws the bars (14 px at the top, 12 at the
bottom) and the panels with the palette and the `bevel_out` of `window.rs`;
what the Hive says (`qs:say`) now appears on the left of the bottom bar while
it lasts, and only over a page does it stay in its own strip, so it can be
read on top of the page. The bars' facts (`World::set_facts`: the machine's
name read from `/proc/sys/kernel/hostname`, the chooser's cores, local time)
are given by `main.rs` twice a second; a test's screen does not have them, so
it shows `--:--` and `1 cores` and the frames are the same on any machine. The
observation says `bars` with the fields filled in.

**In the art.** `hive_screen.py` redraws the cells: a rounded wax body in
relief (a light edge at the top and on the left), a 2 px shadow inside the
24×24 frame, a center that shows the state (honey, empty, cracked, smoke,
off); the colors the VM tapes look for (`#f0aa28` for the honey, `#1c140c`
for the crack) stay the same. `screen.q` reorganizes the comb: a bar at the
top, two columns of cells with a 28 px pitch, the bee between them and the
offers panel, a 308 px notices panel at the bottom, a bottom bar with
`{offers} offers`.

**Proof.** The ten reference frames of `tests/play.rs` were redrawn; the crash
and offer test reads the bars in the observation (`1 cores · effects · --:--`,
`2 offers`, and `fine` after raising the level); the Hive lab's `screen-crash`
and `screen-page` tapes pass. The scene's texts stay in English like the rest
of `screen.q` (the window's help is in Portuguese): a language pass over the
whole screen is left for when the Settings app has the option.

**Next in the slice.** The bottom bar as a taskbar (the open windows) and the
F1 menu with the offers and the apps; then the drawer, the bee that brings the
offer, the zoom into the cell.

## 2026-10-20 - Motion in pixel art: jelly, lamp, curtain

The second step of slice 5: the three transitions Daniel saw animated in the
sketches, now in the daemon, in ticks, without smooth alpha where pixel art
calls for dithering.

**How it is composed.** The window is now drawn once per frame on a canvas of
its own, transparent around it (`World::page_image`), and composited over the
darkened scene: whole when still, deformed during a transition. This costs a
canvas-sized buffer per frame only while there is a page; partial presentation
still takes only the lines that changed to the display.

**The three.** Jelly on opening: the image of the window and its shadow scaled
around the center from 60% to 100% with the `Back` curve (a jolt), the scene
darkening along with it; 12 ticks. Lamp on closing: the window leaves the list
at once (the keyboard goes back to the scene), but its last image bends and is
sucked into the bottom-left corner, each column converging on the target, the
far side folding first; 14 ticks. Curtain when showing the page again after an
action: the new page is drawn whole and the old one stays where a 4×4 ordered
mask has not yet reached; 8 ticks.

**Rules.** Nothing moves at the `plain` level (a single core has no frame to
spare); `HIVE_SCREEN_MOTION=off` in the unit's environment turns it off. The
play protocol got `until still` and the observation says `motion` (kind, tick,
duration); `tests/play.rs` keeps one frame of each transition halfway through
(`window-jelly.png`, `window-lamp.png`, `window-curtain.png`) and proves that
at `plain` the page appears at once.

**What is left for the next steps.** The fold (switching windows) waits for
more than one window; the drawer waits for the F1 menu; the bee that brings
the offer and the zoom into the cell wait for the new comb; spark, shake and
the focus trace come with the widgets.

## 2026-10-20 - The page becomes a window: frame, relief, shadow

The first step of slice 5 (look and motion), after the pixel-art sketches were
approved: the page on the screen stops looking like a terminal and becomes a
window like those of a minimal window manager.

**What changed in the drawing (`window.rs`).** The scene darkens under the
window and shows around it; the window has a 1 px frame with a bevel (light at
the top and on the left, dark at the bottom and on the right for what is
raised; the opposite for what is sunken), a 3 px shadow at 50%, a two-tone
honey title bar with the title in ink and the `Esc` key drawn as a key on the
right, and a raised status bar with the keys that apply. The widgets gained
volume: a sunken field (honey outline when focused), a raised button (focus as
an outline and honey text; primary with honey text; dangerous in red), an 8 px
checkbox with a check mark, a switch with a track and a knob, a radio with a
honey square, a raised select with a three-line arrow, the active tab as a
raised block over a rule, a table with a rule under the header and zebra
stripes, badges and alerts in relief, a two-line rule, a sunken scroll bar
with a raised thumb. All within each cell's 10 px line, so nothing overlaps.

**The window sized to its content.** The width is the canvas's minus the
margins (8 px in the scene, 16 at the fine level); the height is what the
content asks for plus the bars, up to the canvas's limit, and the window is
centered: a short page is a small window over the comb, a long one takes over
the screen and scrolls. In cells: 49 columns and up to 13 lines at 320×180;
100 by up to 29 at the fine level. The play protocol's observation says
`frame` in pixels.

**What stayed the same.** The view tree, the keyboard model, the events: the
page stays the same for every renderer; only the screen draws differently. The
reference frames were redone; the parity test, the Hive lab's tape and the
unit tests pass with no change in logic.

**Next in the slice.** The bottom bar with the windows and the F1 menu, the
comb with bars and panels, and the transitions (jelly, lamp, fold, curtain).

## 2026-10-20 - Pages on the screen, 4b: fine level at 106×36, ABNT2 with accents, scrolling

Slice 4b, on top of 4a, integrated yesterday.

**Fine level.** At the fine level the canvas has two pixels for each one of
the scene's (640×360), and until now the page was drawn with the font in 2×2
blocks, in the same 53×18 cells. Now the page is drawn pixel by pixel on the
canvas (`Band::unscaled`): 106×36 cells, the crisp font, four times the
content. It is the console's `sm` (80 columns): an `hbox` with `stack_below`
stops stacking. When the level changes with a page open, the page reflows into
the new cells and the focus stays where it was (`Window::resize`).

**What the proposal promised and what went in.** The proposal spoke of a
larger font, 8×12, 80×30 cells. The screen's font is a 5×7 face drawn by hand,
glyph by glyph, in `font.py`; a 7×9 face would be 95 new glyphs, plus the
compiler and the schema to carry it to the daemon, and would prove nothing
about the mechanism. On the VM's 1280×800 display, a letter at the fine level
is 12×20 pixels, larger than a text console's font; if in practice it turns
out small, the larger face is the next legibility slice, not this one.

**ABNT2.** The daemon reads `XKBLAYOUT` in `/etc/default/keyboard` on startup
(or `HIVE_SCREEN_KEYBOARD=br` in the unit's environment) and, in the `br`
layout, gives `ç` on its own key, `/` and `?` on the key next to the right
Shift, `;` and `:` where US has `/`, and the accents as dead keys (`´` and
`` ` `` to the right of P, `~` and `^` to the right of Ç, `¨` on Shift+6)
composed with the following vowel, as Latin-1 has them (`ã`, `é`, `ô`, `ü`,
`Ã`...); a dead key and space gives the accent, a dead key and a letter that
takes no accent gives both, Enter forgets the one that was waiting. AltGr
gives `/ ? ° ² ³ ª º`. Caps Lock only flips the letters. All in `input.rs`,
with unit tests; the VM lab's `screen-abnt2.jsonl` tape sets `br` on the
system, restarts the daemon and types `ação` on the real keyboard (a, the ç
key, the ~ key and a, o, Enter): the user's program receives
`"titulo":"ação"`.

**Scrolling and vertical keys.** Up and Down go to the previous and next
element when the one with the focus does not use them (a one-line field, a
button, a checkbox, a tab bar; a radio, a select, a table and a text area keep
them); Home and End go to the first and the last (in a field, to the ends of
the text). Revealing the focus leaves one line of context, and a two-pixel bar
on the right edge tells where the screen is in a long page.

**Outside this slice.** Stream and history stay as text; the 7×9 face.

## 2026-10-19 - Pages on the screen: `quantum pixel`, slice 4a

The Hive's screen now also shows the machine's applications. `quantum
pixel`, run by any local user in a project's folder, is the fourth
renderer of a Quantum page, alongside the browser, the console and the
desktop: the same runtime (the application's server, opened in-process
as `quantum console` does), only the drawing changes.

**How it works.** `quantum pixel` connects to the daemon's socket
(`/run/hive-screen/pixel.sock`, mode 0666 in the unit's `RuntimeDirectory`),
sends each page as the view tree in JSON (`show`, whole, on every
change) and receives what the user did, one line per event: `click`,
`submit` (with the form's fields as a browser would post them),
`change` (search field, after the pause), `navigate`, `reload` and
`close`. The daemon (`window.rs`) lays the page out in font cells (53 by
17 in 320×180), draws it over the scene and owns the keyboard while it
is showing. The keyboard is now read entirely from `/dev/input` (US
layout, Shift, Caps Lock, repeat); ABNT2 and dead keys are left for 4b.

**No mouse.** Four rules, and no keys beyond the console's: Tab and
Shift+Tab move between the elements that react, in page order (the
focused one in honey); arrows move within one (cursor in the field,
radio/select option, table row and button, tab); Enter activates (in a
field, it submits the form); Space checks; Esc closes the page, the
scene comes back whole and `quantum pixel` exits. The last line says
which keys apply to whatever has the focus. A page shown again after an
action keeps the focus on the same element, recognized by what it is
(type and `bind`/text), not by its number, which changes when a flash
or an error enters the tree.

**How it is proven.** The UI-7 parity test runs the same script (sees,
fills in, checks, picks, clicks) on a third driver, the screen's:
`hive-screen` in play mode with `--pixel-socket`, the keys through the
protocol and `quantum pixel` as the page's runtime in a thread; the OS
workflow runs this test against the freshly built binary.
`tests/play.rs` keeps a reference frame of a page (`window.png`); the
Hive lab reads a page as data (`screen-page.jsonl`, with `contains` in
the `screen` op to assert a field of an event); the VM lab takes a page
from an ordinary user's program to the real screen, types into it
through the real keyboard and sees the form come back with what was
typed (`screen-pixel.jsonl`; `press` now accepts all keys and `type`).

**What was left out.** A larger font at the fine level and reflow per
level, ABNT2 and dead keys, more polished scrolling (4b); F1 with the
Hive's offers over the app, an OS Settings app, multiple windows, offers
that open pages (4c).

## 2026-10-19 - The screen presents only what changed, and shares the console

Two consolidations of the screen, after the three slices.

**Only the rows that changed.** A scene at rest is not still: the bee
flaps its wings ten times per second, and each flap cost a whole frame,
1280×720 pixels (4 MB) written to the scanout buffer and transferred
through `virtio-gpu`. Now the display keeps the last frame presented and
compares it row by row (`changed_rows`): only the band between the first
and the last differing row is scaled up, written and marked dirty. The
bee costs 16 rows out of 180. A frame equal to the previous one does not
touch the buffer. The fine level with snow still costs the whole frame,
as it should: there everything changes. Measured in the VM lab under
emulation, where nothing is fast: the bee's frame at level 1 cost 75 to
100 ms and went down to 20 ms (the line the daemon writes in the
journal, `ms a frame over the first 20 frames`). That is still the limit
of the budget at 30 fps under TCG, so the levels tape still requires
KVM; on a real machine the difference is the same proportion over costs
ten times smaller.

**The console is shared.** Until now `hive-screen` held `tty1` and did
not handle Ctrl+Alt+F2: the serial console and SSH were the way to reach
grove. Now the terminal is in `VT_PROCESS` mode: the kernel sends a
signal before switching, the daemon releases DRM (`DROP_MASTER`, so the
text console can draw on the same card), answers `VT_RELDISP` and waits
without drawing and without accepting keys; on the signal to come back,
it takes master again (whoever was master can become it again without
privilege), sets the mode again and draws the whole frame. The
`screen-vt.jsonl` tape does `chvt 2` in the guest, waits for the honey
to disappear from the `screendump`, does `chvt 1`, and waits for the
honey to come back. `until_shot` gained `lacks`, waiting for a color to
disappear.

## 2026-10-19 - The screen grows with the cores: presentation levels

The screen's third slice, the experimental requirement: the interface
scales with the cores the VM gives. It is not "making a GPU", it is
flexibility. How much `hive-screen` shows is a **presentation level**
(`level.rs`), chosen while it runs by the frame time it measures, never
above the ceiling the cores allow:

| level | needs | shows |
|---|---|---|
| 0 `plain` | 1 core | the scene as declared, without particles, at most 15 frames per second |
| 1 `effects` | 2 cores | the particles (`qs:emit` and the `qs:emitter`s with `level="1"`), at most 30 |
| 2 `fine` | 4 cores | two pixels for each one of the scene's: a tween or a particle lands on its own pixel, the font becomes blocks; and the `qs:emitter`s with `level="2"`, the snow the OS scene keeps for this level |

A level changes how the scene looks, never what happens in it: the same
ticks run at any level, the rules do the same. The one that chooses is
the `Chooser`: the moving average of a frame's cost (drawing plus
presenting) below 15% of the level's period, for at least 20 frames and
2 seconds, moves up one level, if the cores allow it; above 60% it moves
down, and a level that proved expensive is only tried again half a
minute later. The cores come from `available_parallelism` twice per
second (the process's affinity and the cgroup's quota): a vCPU that
comes in by hotplug counts within half a second, one that leaves drops
the level at once. A still scene still costs nothing at any level: only
a drawn frame is measured.

The frame is drawn in bands of rows, one thread per core (up to eight,
`std::thread::scope`): each band draws the same list of nodes clipped to
its rows, so the image is the same with one band or forty, and the test
proves it pixel by pixel at ×1 and at ×2. Scaling up into the DRM dumb
buffer also goes by bands. At the fine level the canvas has `scale`
pixels per scene pixel, and the primitives receive scene coordinates:
`fill_rect_f` for the particles (fractional position and size), `blit`
and `text` multiply. At ×1 the math is exactly what it was before: the
`main` scene drawn by the new daemon matches the old references pixel by
pixel (the `crash` and `offer` references changed only because the scene
gained an emitter and the bursts' seeds moved one place).

In the language, one thing: `qs:emitter level="1|2"`, the lowest level
at which the emitter plays (1 by default; 3 is refused, citing the
line). The OS scene gains `<qs:emitter particles="snow" level="2">`. The
play protocol gains `{"op":"level","level":N}` and `frame` accepts
`bands` (the test draws the fine frame whole and in 3 and in 8 bands
against the same reference).

In the VM lab the machine goes to 4 vCPUs (`BASE_VERSION` 6) and the
`cpus` op leaves 1 to 4 of them online in the guest
(`/sys/devices/system/cpu/cpuN/online`), waiting for `nproc` to agree:
to a program, an offline vCPU is what a switched-off one would be, and a
`restore` brings back the snapshot's ones without ceremony. QEMU's
hotplug was the first attempt (`-smp 2,maxcpus=4`, `device_add` of the
slots from `query-hotpluggable-cpus`): `device_add` succeeds, but this
guest's kernel boots with `smpboot: Allowing 2 CPUs, 0 hotplug CPUs` and
never sees the new one. `shot` gains `lacks`, the color that must not be
on the screen. The `screen-levels.jsonl` tape follows the level with the
cores: 2 online and `cores: 2, level up to 1`, the screen without snow;
4 online and `cores: 4, level up to 2`, then `level 2 (fine)`, the scene
at ×2 on the display and the snow's color in the `screendump`; 2 again,
level 1 and the scene at ×4 once more. This tape says `// needs: kvm`
and the lab skips it where `/dev/kvm` is not usable (CI has it): under
emulation just presenting the 1280×800 buffer costs 80 ms per frame, the
budget belongs to the emulator and not to the machine, and the screen
honestly stays at `plain` with any number of cores (the ceiling,
`cores: 4, level up to 2`, shows up just the same). For whoever knows
better than the measurement, or to take a capture, `HIVE_SCREEN_LEVEL=N`
in the unit's environment pins the level.

On top of that, three things. The scanout buffer was mapped (`mmap`) on
every frame, and a new mapping costs one page fault per page: under
emulation that was 128 ms per frame, which dropped the screen to `plain`
with two cores; now it is mapped once, for the life of the display
(`drm-ffi` gives the offset, `libc::mmap` the rest). The daemon's loop
consumed `dirty` before looking at the clock, so a single change within
the 33 ms after a frame was lost until the next one (the animations
masked it); now the clock comes first. And a `done.actual.png` that had
ended up in the repository was removed, with `*.actual.png` in
`.gitignore`. The daemon writes in the journal, once per visit to a
level, how much a frame costs there. And the console tape waits for the
cell's crack (`#1c140c`, a color in no other frame, which stays until
the honey comes back) instead of the smoke, which lasts 1.5 s and which
the journal queries under emulation sometimes missed.

This slice's limit: there is no level above fine; more cores than four
only give more bands. A `smooth` level at 60 frames per second would fit
in the same table once there is something to show with it.

## 2026-10-19 - The Hive's screen on the real console (DRM, keyboard, unit)

The screen's second slice: `hive-screen` draws on the VM's console. No
X, no Wayland, no GPU driver on our side: it opens `/dev/dri/card0`,
takes the first connected connector in its preferred mode, creates a
dumb buffer and writes the scene into it, scaled up by an integer and
centered (1280×720 is ×4 of 320×180; 1024×768 is ×3 with black
borders). It draws only when the frame changed, at most 30 times per
second: a still scene costs nothing. The keyboard comes straight from
`/dev/input` (the `event*` devices that have Enter), and the `tty1`
terminal, which systemd gives the daemon as standard input, goes into
graphics mode (`KDSETMODE`) while it runs, and back to text on exit,
including on SIGTERM.

`hive-screen.service` runs as `_hive-screen`, its own user in the
`video` and `input` groups, with the same hardening as the other
daemons, `DevicePolicy` closed except for the card, the input events and
`tty1`, and `Nice=5` and `CPUWeight=50` to give way to the synapse. The
cortex accepts `hive-screen` as a dashboard when it comes from that uid
(or from an administrator, as before). Installed by the VM lab, the ISO
and the package, with `/etc/hive/screen/`.

The VM lab gained a `virtio-gpu` card (the base is rebuilt:
`BASE_VERSION` 4), the `shot` op, which reads the display through QMP's
`screendump` and counts the colors (a thirty-line PNG decoder, standard
library only), `until_shot`, and `press`, which presses keys on the
machine through `send-key`. The `screen-console.jsonl` tape follows a
real crash: the title in honey on the display, the grey smoke over
nginx's cell, the offer reaching the daemon (in the journal), Enter on
the machine's keyboard, the actuator really restarting and the honey
back in the cell. Data and colors, not OCR.

On top of that, a bug in the VM lab agent's transport: a short timeout
left on the socket by an earlier wait cut off the next request, which
only showed up without KVM, when the first boot takes a while. Now each
request sets its own.

## 2026-10-19 - The Hive's screen: pixel art on the console, declared in Quantum (qs:)

The OS's graphical interface, decided after weighing Godot in the VM
(Mesa llvmpipe, a compositor, ~300 MB and a C++ engine as a client that
approves actions) against a runtime of our own: the runtime of our own
won, with no overhead at all. What the console shows is a
`q:application type="screen"`, `config/screen/screen.q`, with `qs:`
tags:

- `qs:sheet` and `qs:animation` are the frame sheets and their cycles;
  `qs:particles` an effect (the same presets as the games); `qs:scene`
  what is on the screen: `qs:sprite`, `qs:text`, `qs:emitter`, and two
  built-in widgets, `qs:offers` (the Hive's offers, which the
  administrator approves with the keyboard; a dangerous action asks for
  Enter twice) and `qs:notices`.
- `qs:on event="..."` says what happens in the scene when an event
  arrives: `qs:animate`, `qs:frame`, `qs:show`, `qs:tween` (the same
  curves as the games), `qs:emit`, `qs:say`. The events are those of the
  `qh:` rules, with the same `{fields}`, plus `notice`, `offer`, `done`
  and `failed`. A sprite's name is how a rule reaches it: `{service}` in
  `service-crash` finds the sprite named `nginx`, and it puffs smoke.
- No statements or expressions. The compiler (`quantum/runtime/screen`)
  refuses, citing the line, whatever the file cannot fulfill: a sheet
  that does not exist, a frame it does not have, a field the event does
  not have, a target that no sprite is named.
- The font is ours: 5×7 pixels in 6×10 cells, ASCII and Latin-1 with the
  accents composed from the base letters, written as `font.png` next to
  the scene. The art (a comb of honeycomb cells, one cell per service, a
  bee) is from `scripts/art/hive_screen.py`, CC0.

The daemon is `crates/hive-screen`: it loads `screen.toml` and the
sheets (PNG), plays the scene at 60 ticks per second on a canvas, and is
a client of the cortex's user socket like the dashboard (the cortex
accepts it as one). For the screen to react to what happened and not to
the words, `Notification` now carries `kind` and `fields`: the event
table that lived in the synapse moved to `hive-common` (`events.rs`),
and the cortex fills in the fields in each notice. The actuator's reply
becomes `done` or `failed`, with the action's name and the service or
package.

Determinism: sine, cosine and 2^x are pure arithmetic in the daemon, and
the particles use a fixed seed, so a frame is identical pixel by pixel
on any machine. The daemon's test (`tests/play.rs`) plays the OS screen
through the play protocol (stdin, like the games' driver) and compares
four frames with references; the Hive lab runs the real `hive-screen`
without a display (`{"op":"screen"}`) and reads what it shows as data:
the `screen-crash.jsonl` tape follows nginx going down, the smoke in the
cell, the offer, the Enter, the actuator and the honey back in the cell.

Left for the next slices: drawing on the real console (DRM/KMS, keyboard
through evdev, a systemd unit with the `_hive-screen` user), the lab's
VM with `virtio-gpu` and `screendump`, and the presentation levels by
frame budget, so the scene gains resolution and effects with the cores
the VM gives.

## 2026-10-19 - The Hive's rules declared in Quantum (qh:)

What really ties the two projects together. What the Hive offers when
something happens (restarting the service that went down, showing the
logs, installing the package the user asked for) lived in Rust code in
the synapse (`actions.rs`), and the actuator's whitelist in a separate
TOML. Now both are one Quantum file, `config/hive/hive.q`, with `qh:`
tags:

- `qh:on event="service-crash"` holds an event's offers; `qh:offer` is
  an offer with a title, a description, `action=` (the kebab-case name
  of the actuator's `Action` variant) and that action's attributes. Any
  of them can contain `{field}`: a field of the event, which the synapse
  fills in from the event itself, never from the model's text.
- `qh:allow`, `qh:block` and `qh:limit` are the whitelist: what the
  actuator may do, what it may never do, and how many times per minute.

**The compiler refuses what the file cannot fulfill:** an event, an
action or an attribute that does not exist; a `{field}` the event does
not have, or text where a number goes (`port="{holder}"`); an offer the
file's own whitelist would refuse (a command without
`qh:allow command=`, a blocked service, a `kill-port-process` without
the permission); statements, expressions or script. Twenty-two cases in
`tests/hive/`.

**What comes out:** `config/hive/rules.toml` (new; the synapse loads it
from `/etc/hive/rules.toml`, and the build embeds the committed file as
the default rules) and `config/hive/whitelist.toml` (the same format as
before, now generated). `python scripts/generate-hive-config.py` writes
both; a test fails if they are edited by hand or if `hive.q` changes
without regenerating. The generated whitelist is identical to the one
that existed (compared as TOML). The synapse gained `rules.rs`, which
runs the same checks on load and falls back to the embedded rules if the
file is invalid; an offer whose value is not what the action accepts at
run time is left out, never guessed.

**Around it:** the language is laboratory, like the games;
`docs/targets/hive.md` is generated from the schema; the `hive_rules`
feature module has intents and a dataset (5 positives, 12 negatives),
and a test ensures that every tag, event and action has an intent and an
example. The Hive lab gained the `log-anomaly` tape: the fifth rule,
which had no tape. What was left out: the cortex's 5-minute window
(`report-interval`) is still a constant in the code; it becomes an
attribute when the cortex loads the file too.

## 2026-10-19 - VM Lab: the real system, restored in a second

The second layer of the OS's play protocol. The Hive lab validates what
the Hive decides, but not what only the running system shows: what the
real nerves see in the journal, in the audit and in `/proc`, and what
the real actuator does through polkit and systemd. The ISO lab covered
that with the ISO, installation, OCR and the Forge, at minutes per
round.

**What it is (`scripts/lab/vm/`, documented in the README there and in
CLAUDE.md):** Ubuntu 24.04's minimal cloud image (the release the OS
remasters) on a qcow2 overlay, in QEMU (KVM when there is one, emulation
when not). cloud-init only installs an agent: `agent.py`, which speaks
JSON lines over a virtio-serial port, with no network, no SSH and no
keys. The base boots once and becomes the `base` snapshot, with polkit,
PackageKit and auditd. The host downloads those packages using the
guest's own dpkg status, and the guest installs them offline over 9p.
The working tree's Hive (binaries without debug info, `config/`) is
installed the way the ISO installs it (`install-hive.sh`) and becomes
the `hive` snapshot. Each tape restores `hive`. The real dashboard and
grove run in a terminal inside the guest, and the new `hive-lab term`
reads the screens with the same emulator as the Hive lab.

**Timings, measured here without KVM:** the base comes out in ~5 min
(almost all of it is the first boot). Bringing up the VM from `hive`
takes ~7 s, and a restore ~2 s. The six tapes take ~115 s together. Only
what changed is installed: if only binaries changed, they are copied and
only their units restart (grove 6 s, a nerve 9 s, the cortex 20 s,
versus 60 s for the full installation). **In CI, with KVM:** the base
comes out in 18 to 25 s, and the six tapes, with the first installation,
in ~60 s (without it, 2 to 7 s each).

**Tapes:**
- `crash-restart`: a real unit in a crash loop shows up once in the real
  dashboard, and only after it is approved on the keyboard does the real
  actuator restart the unit through polkit.
- `port-conflict`: a real process holds the port, the real network nerve
  names both once, and the actuator runs the approved `ss -tlnp`.
- `dangerous-command`: a logged-in user's `rm -rf /srv` goes from the
  kernel's audit to the real dashboard. A routine delete and daemons'
  commands are not reported (the audit rule only records whoever has a
  loginuid, and the agent gives a loginuid to the user's commands, as a
  login would).
- `crash-loop`: a unit in a crash loop shows up, and so does the restart
  offer, only once.
- `anonymous-shell`: with the real grove in anonymous mode, a dangerous
  command reaches the process nerve through the audit, and the cortex,
  walking up the real process tree to the shell, passes nothing on.
  Outside anonymous mode, the same command is judged again.
- `install-on-request`: the user calls htop in the real grove, the
  dashboard offers the installation, and the approval makes the
  unprivileged actuator install through PackageKit and polkit, from a
  signed repository inside the guest (its only package source, mounted
  by the host). On the second try grove runs htop.

A tape that mixed the crash loop with the approval failed once in CI
with KVM: systemd's auto-restart and the approved restart were competing
for the same window. Approving right after fixing the cause, with the
service coming back on its own, is a legitimate race. That is why the
loop and the restart became separate tapes, and the restart starts from
a unit that went down once. The same operations are MCP tools
(`vm_start`, `vm_request`, `vm_view`, `vm_tape`, `vm_end`).

**What the lab found:**
- A unit in a crash loop flooded the Hive. Each crash went to the model
  and stacked "Service Crashed" and the offers in every dashboard (42
  restarts, 42 notices and on top of that a port conflict with offers
  for each one). Now the cortex passes the same problem on once every 5
  min, and the following report says how many it held back, as it
  already did with the package offers. There is a test in the router and
  a `crash-loop` tape in the Hive lab.
- The network nerve already had a 5-min window, but the key included the
  pid, which changes on every restart, so it never held anything back.
  Now the key is the unit (or the program), with a test.
- After an `rm -rf /srv`, the dashboard said "A ZFS snapshot has been
  created for safety", on a system without ZFS. The text of the
  synapse's mock claimed something that nothing does. The line was
  removed, and a test keeps the mock from claiming anything.
- A service action that failed reached the dashboard as "(failed)" and
  the journal as an exit code, because what systemctl said was
  discarded. Now that becomes the action's output.
- The druidos-hive package did not depend on what the Hive uses. On a
  system without `packagekit-tools`, the approved installation failed
  with "Failed to run pkcon", and the ISO only worked because it
  happened to ship that package. `debian/control` now depends on
  polkitd, packagekit, packagekit-tools and auditd.

## 2026-10-19 - Hive Lab: the Hive in a box, without a VM (the start of Quantum OS)

The user's request: start Quantum OS from DruidOS with what was holding
the project back the most, which was validating ideas. Each round needed
an ISO, a boot, an installation, OCR and the Forge; in a cloud session
(no KVM, no access to the Forge) nothing could be validated.

**What it is (`crates/hive-lab`, documented in CLAUDE.md and in the
crate's README):** the real `hive-cortex` and `hive-synapse`, and the
rest played by a driver that speaks one JSON request per line. A nerve
injects typed events, grove asks and the dashboard approves. The
actuator records the `ActionRequest` without executing anything and
replies "recorded, not executed". Each role connects with the binary
name and the user that the cortex checks (`_hive-sense`, `_hive-act`,
root for the dashboard), so the identity rules are the system's. The
Hive's users exist only in the lab: each daemon runs in a private mount
namespace with the lab's `/etc/passwd` and `/etc/group` mounted on top,
and the machine's `/etc/passwd` is not touched. That is why it needs
root (a container, a disposable VM, CI with sudo).

**Timings:** the session comes up in ~0.2 s. The 6 tapes in
`crates/hive-lab/tapes/` run together in ~4 s: crash → restart only with
approval; program not found → install only with approval; port
conflict; full disk; a question answered as text and never as an
action; and the boundaries of the user socket (grove sends no action and
approves no suggestion). A session made by hand becomes a tape with
`--record`. `scripts/lab/hive-tapes.sh` runs them all, and CI gained
that step.

**What the lab has already found:** without the model, the synapse
replied "Check package info with `apt show PACKAGE`" with a literal
`PACKAGE`, and the same with `SERVICE`, `PORT` and `KEYWORD` (the mock
mode's text). In a port conflict it did not even pick the port text,
because the event's description says "already held by" and not
"conflict". Fixed: `fill_mock_names` fills in the names from the event
the prompt describes, and a line that would be left without a name is
omitted. The `command-not-found` and `port-conflict` tapes now require
`apt show htop` and `lsof -i :80` without any placeholder (`excludes`),
and fail with the old code.

**Screens as text (same day):** the lab runs the real `hive-dashboard`
and `grove` in a pseudo-terminal, and reads the screen through a
terminal emulator (the `vt100` crate): `tui`, `view`, `keys`,
`until_screen`. No screenshots and no OCR. On the first look at the real
dashboard, two defects:

1. Every notice without a suggestion showed up in red with "(CONFIRM?
   press Enter again)": `armed == r.suggestion.map(...)` is true when
   both sides are `None`. Now `is_armed()` requires both to be `Some`.
2. The cortex sent notices and suggestions only to the **first**
   dashboard in the HashMap. With two administrators, which one saw them
   depended on the HashMap's order. Now they go to all of them. The
   first approval takes it (`pending_suggestions.remove`), so nothing
   runs twice. There is a test in the router, which failed before.

New tapes: `dashboard-screen` (fails with the old dashboard, checked)
and `grove-screen`. All 8 run in ~5 s.

**Next layers:** this lab's boundary is what the real system does. What
the nerves notice on a running system and what an action does call for
a light VM (Ubuntu's cloud image, an agent over vsock with structured
observations, the grove and dashboard screens as text through a pty and
a vt100 emulator, no OCR, snapshots through QMP). After that, an MCP
server with the same tools as Quantum's play protocol.

---

## 2026-09-10 - ISO Lab: build → boot → install → e2e with no human, on the Forge with KVM

User's request: an environment where Claude can build the ISOs, boot them
in QEMU and test end to end on its own. Before this, not even the boot of
the 24/08 ISO had really been confirmed (only "QEMU's memory growing").

**Infra:** the Forge (VM 400) had no `/dev/kvm` — CPU `x86-64-v2-AES`.
The Proxmox host already had `nested=1`; I changed the VM's CPU to `host`
and rebooted it via `qm reboot` (the 40 containers came back). Alternatives
ruled out: VMs directly on Proxmox (only ~2GB of free RAM, and the router
runs there), TCG (~1h per install), local QEMU on Windows (the Colossus is
itself a VM, WHPX doesn't work).

**The lab (`scripts/lab/`, documented in CLAUDE.md):** `lab.sh` (local,
syncs the working tree) → `remote.sh` (Forge, one detached container per
stage, survives an SSH drop) → `harness.py` (QEMU via QMP: screendump +
OCR with tesseract for the screen-only phases, serial log, SSH into the
guest) → `e2e/guest-checks.sh` (runs inside the installed DruidOS, TAP
output). Real times with KVM: ISO ~1 min (base.iso cached), boot to the
installer ~20s on BIOS and UEFI, automatic install ~3 min, e2e ~40s,
`dev` loop (build + hot-swap of the binaries + e2e) ~1 min, full `all`
pipeline 5min50s.

**What the lab found (all fixed):**

1. **The ISO installed plain Ubuntu.** Subiquity installs what is in
   `casper/install-sources.yaml`, which only listed Ubuntu's original
   layers — the `filesystem.squashfs` with the Hive Stack was never used.
   Now `register_install_source()` registers `druidos` as the only source.
2. `build-iso.sh`: the `hive-*` glob copied cargo's `.d` files to
   `/usr/bin` and left `grove` out; it only enabled `hive-cortex`; it
   copied the unversioned `config/hive/config.toml` (with `user = "lab"`),
   and the path of `druidos-installer` was wrong. Now an explicit list of
   binaries (missing = error), the 7 services enabled, `default.toml`
   installed as `/etc/hive/config.toml`.
3. **No service came up.** All the units are `Type=notify`, but no binary
   sent `READY=1`: `hive-cortex` stayed in "activating" until the timeout
   and the other 6 failed through the dependency. New
   `hive_common::systemd` (sd_notify protocol, no new dependencies, with
   tests) called by the 7 daemons when they are ready. The e2e was run
   first against the disk with the bug (15 failures) and then with the
   fix (24/24).
4. `hive-synapse.service` had an inline comment in a value
   (`MemoryDenyWriteExecute=no  # ...`) — systemd doesn't support that, so
   the whole line was ignored.
5. Serial console: the ISO's GRUB and the kernel now also on `ttyS0`
   (inherited by the installed system), consistent with
   VM-first/terminal-only.

**Continued (same day) — fixes guided by the lab.** Method: first the e2e
check (red against the previous build), then the fix (green), then
`lab.sh all` from scratch.

- `hive-nerve-fs` observed nothing: it ignored the config; `notify`'s
  recursive watch aborts the whole tree at the first unreadable directory
  (`/etc/credstore` for `_hive-sense`); and it expected
  `Modify(Data(Content))`, which the inotify backend never emits. New
  `tree::watch_tree` (one watch per directory, skips only the unreadable
  ones, new directories get a watch), writes detected by
  `IN_CLOSE_WRITE` and by rename (editors, `sed -i`).
- The cortex dropped every `Notification` coming from nerves (no arm in
  the router). Now it forwards them to the dashboard, discarding `actions`
  and rejecting senders that are not nerves.
- `hive-nerve-journal` re-read the last 10 entries on every start
  (`--follow` without `--lines=0`).
- ANSI colors in the journal: a shared `hive_common::logging::init()`,
  color only when stdout is a terminal.
- New e2e checks, including the approval flow in `hive-dashboard` driven
  by tmux (Enter on a suggestion → the cortex receives the `UserAction`).
  One check was passing falsely (`grep $'\x1b['` without `-F` exits with
  error 2).

**Continued — approving a suggestion now really acts.** Until now
`hive-actuator` was unreachable in the product: the synapse only produced
text (`action: None`), and even with an action the actuator (user
`_hive-act`, no root) couldn't `systemctl restart` ("Interactive
authentication required" — confirmed in the guest with the new
`lab.sh exec`).

- `hive-synapse/src/actions.rs`: fixed rules from the typed event to typed
  actions (service crashed → `RestartService` + logs; anomaly → logs;
  disk → `df -h`; port → `ss -tlnp`). Parameters come from the event, never
  from the model's text; unit names are validated.
- `config/polkit/60-druidos-hive-actuator.rules` (installed by the ISO): an
  OS-level ceiling under the actuator's whitelist — only
  start/stop/restart/reload of `.service`, never
  hive-*/systemd-*/dbus/polkit/ssh/getty/user@.
- `hive-nerve-journal` attributed every service failure to `init.scope`
  (PID 1's messages have the real unit in the `UNIT` field).
- End-to-end e2e on a clean install: a whitelisted service crashes →
  "Restart" suggestion → Enter in the dashboard (tmux) → the actuator
  restarts it via polkit; and polkit refuses `_hive-act` outside the
  ceiling (the refusal has to be an authorization one, otherwise the check
  proves nothing). 40 checks green.

**Continued — `hive-nerve-network` redone.** The old one only produced
false conflicts (two LISTEN sockets on a port = "conflict", which is every
dual-stack service; confirmed in the guest) and never saw a real one
(whoever loses the bind gets no socket; PID fixed at 0). Now the conflict
is detected from the side of whoever lost: `journalctl --grep` for
"Address already in use"/EADDRINUSE, port extracted from the message
(nginx, apache, redis, node, sshd, python formats; no port = ignore, a
time of day never becomes a port), requester from the journal's trusted
fields (`_PID`, `_COMM`, `_SYSTEMD_UNIT`), port owner via `/proc/net` — by
user, because `_hive-sense` can't map another user's socket to a PID
(verified in the guest). `Restart=always` retries are reported once every
5 min. Empty `watch_ports` = all ports (new default); the unit gained
journal read access and lost `CAP_NET_ADMIN`. The notification says who
failed and who holds the port. Three e2e checks (red before, green
after); also fixed a flaky `nerve-journal` test (a logging process that
exited before journald resolved its cgroup). 43 checks green on a clean
install.

**Continued — `hive-nerve-process` no longer misses fast commands.**
Polling `/proc` every 250ms caught 0 of 20 back-to-back `rm -rf` on a
real install. The proc connector wouldn't solve it (it only delivers the
PID; reading the cmdline afterwards has the same race). Now the nerve
reads the kernel's audit: the ISO installs `auditd` with the rule
`config/audit/60-druidos-hive-exec.rules` (every `execve` from a login
session — `auid` set: SSH, console, sudo; not daemons/cron/package
scripts) and the nerve subscribes to the audit multicast group via
netlink with `CAP_AUDIT_READ` (only reading audit records, nothing
more). The argv comes from the kernel at the moment of the exec. An
attempt to read it through the journal was dropped: Ubuntu disables
`systemd-journald-audit.socket` on purpose. New module `audit.rs`
(assembles SYSCALL+EXECVE+CWD by serial up to the EOE; arguments in hex
and in chunks; tested with records captured from the guest); without
audit, fallback to polling with a warning. Now it catches 20 of 20. The
e2e also showed an observer effect: the check's own `grep` has
`rm -rf /tmp/...` in its argv and is (correctly) reported. Note:
`/var/log/audit/audit.log` (root only) now stores users' command lines.
45 checks green (correction: the earlier totals were 40 and 43, not 42
and 45).

**Continued — the two remaining findings.**

- **Dangerous command judged by what runs, not by text.** The regex over
  the whole line flagged `grep "rm -rf /"` and `rm -rf /tmp/build`, and
  missed `cd /etc && rm -rf nginx`. New `danger.rs`: the real program
  (the audit's `exe`, not argv[0]), parsed arguments (clusters,
  `--recursive`, `--`; for chmod/chown only `-R`), operands normalized
  against the `cwd`, and an explicit definition of dangerous (`/`, a
  top-level directory, or a direct child of a system directory —
  /etc/nginx, /home/alice, /usr/lib). The e2e canaries are now real,
  harmless `rm -rf`: `rm -rf /etc/<name>/..` normalizes to /etc, but the
  directory doesn't exist and GNU rm refuses `..` (verified in the
  guest).
- **Real priority in the journal.** `hive_common::logging::init()` sends
  to the native journald (`tracing-journald`) when stdout is the journal
  (`JOURNAL_STREAM` compared with stdout itself): WARN/ERROR get priority
  4/3. Before this, `nerve-journal` was changed to ignore logs emitted by
  `hive-*` units (PID 1's messages *about* them still count), otherwise a
  warning from the Hive would become an anomaly reported to the Hive
  itself.

50 checks green on a clean install.

**Findings still open:** none of the ones raised in this session.

**Continued — the three priorities: grove, a real model, ZFS.**

- **`grove` runs programs** (`79e8514`, e2e in `aab4dde`). Until now it
  only had builtins. New parser (words with quotes and parts, lists with
  `;`/`&&`/`||`/`&`, pipelines, redirections `<` `>` `>>` `2>` `2>&1`),
  expansion (variables, `~`, glob), execution with real pipes, builtins
  inside a pipeline (in a thread), background jobs, and interactive shell
  signals: Ctrl-C stops the foreground program and not the shell
  (verified in the guest via tmux). `grove -c` and scripts too. Commands
  run by grove are seen by `nerve-process` like any other.
- **`hive-synapse` runs a real local model** (`0842ebf`, e2e in
  `c70cdc3`). `candle` backend (the user's choice, pure Rust) with
  Qwen2.5 0.5B Instruct Q4_K_M (GGUF, 491MB) and the tokenizer, pinned by
  sha256 and embedded in the ISO by `build-iso.sh` (cached in
  `~/druidos-lab/cache/models` on the Forge). A short chat prompt (every
  prompt token costs time on a VM's CPU), a request queue that drops the
  oldest (at most 3 pending), and the actions still come from the typed
  rules, never from the model's text. Measured in the VM (2 vCPU): load
  ~1s, 11–17s per answer, a peak of ~1.56GB (`MemoryMax=2G`), no OOM. The
  checks that depend on an answer wait for the synapse to empty its queue.
  54 checks green.
- **ZFS as root, real safety snapshots.** Before: the lab installed ext4
  (`layout: direct`); the actuator tried
  `zfs snapshot rpool/ROOT/druidos@...`, a dataset no installer creates,
  as `_hive-act` without permission, and went ahead with the action when
  it failed (just a warning); on top of that, "destructive" was every
  `RunCommand` (including `journalctl`) and didn't include installing or
  upgrading packages. `hive-apt` only printed a suggestion with the same
  wrong name. On a real ZFS install from the lab: root on
  `rpool/ROOT/ubuntu_52tka7` with 15 child datasets (`var/lib/dpkg`,
  `var/lib/apt`, `var/log`...), `/boot` on another pool
  (`bpool/BOOT/ubuntu_52tka7`), and `_hive-act` gets "permission denied".
  - Lab: the autoinstall uses `layout: zfs` (`--storage`, `direct` is
    still available); the golden disks got the `-zfs` suffix; the
    hot-swap also installs `/etc/hive/{config,whitelist}.toml`.
  - `hive_common::zfs`: the system datasets (`/` and `/boot`) read from
    `/proc/self/mountinfo` (the test fixture is the guest's real
    mountinfo), name `hive-before-<change>-<UTC time>`, `zfs snapshot -r`
    per dataset.
  - `hive-actuator`: snapshot before installing/removing/upgrading
    packages (`Action::should_snapshot_first`, which lost
    `RestoreSnapshot`: the `rollback -r` would destroy the freshly created
    snapshot), and **refuses the action if the snapshot fails**.
    `ExecStartPre=-+hive-actuator delegate-snapshots` applies
    `zfs allow -u _hive-act snapshot,mount` as root on the datasets at
    every start. `snapshot_dataset` became optional (empty = detect).
  - `hive-apt install/remove/upgrade/autoremove` actually takes the
    snapshot (after the confirmation, before apt), and aborts if it fails
    (`--skip-hive` skips it). `hive-zfs` also detects the dataset.
  - The lab found two problems along the way: ZFS refuses a snapshot of
    two pools in a single call ("multiple snapshots of same fs not
    allowed", even without `-r`), so it's one call per dataset; and the
    automount of `.zfs/snapshot` gives ELOOP on a child dataset, so the
    e2e reads the snapshots by mounting them read-only.
  - 7 new checks (red before: 5 failures): root is ZFS; the actuator finds
    the datasets; `_hive-act` can take a snapshot and ZFS refuses
    `destroy` and `rollback` for it; `hive-apt install` of a local `.deb`
    creates the snapshot on both pools, and the snapshot (root + the dpkg
    child) has neither the file nor the package's record, while the live
    system has them; `hive-apt remove`, the reverse.
  - Pending: cleanup/retention of the `hive-*` snapshots (`hive-zfs` has
    the logic but no unit), ZFS as the default in the interactive
    installer (only the lab's autoinstall picks it), and the actuator's
    path is only covered by unit tests (no current suggestion offers a
    package action).

**Continued — next steps: push, docs, ZFS in the ISO for real, grove ↔ Hive.**

- Pushed the 8 commits (CI and the ISO build green at `3f3f929`) and
  corrected CLAUDE.md: the real base/kernel/bootloader (Ubuntu 24.04,
  Ubuntu's kernel, GRUB — the lean kernel and systemd-boot remain the
  goal), grove already runs programs, two-press confirmation in the
  dashboard already exists.
- **The production path had never been tested.** The lab's `install`
  skips the installer (direct kernel boot + autoinstall). New
  `lab.sh install-interactive`: boots the ISO as a CD, picks the GRUB
  entry and walks through Subiquity's screens with keys via QMP,
  recognizing each screen by its body text (OCR) and with the keys chosen
  by the focus rules read from Subiquity's source code (extracted from
  the ISO itself); then it boots the disk and judges the `root=` from the
  serial console. The OCR got a second, thresholded pass, because the
  orange bar and the focused green button disappeared. Red: the default
  install created LVM/ext4 (`root=/dev/mapper/ubuntu--vg-ubuntu--lv`) —
  no safety snapshots for anyone installing the ISO for real.
- **ZFS by default in the ISO.** Subiquity's disk screen only offers LVM
  or a plain partition and ignores the autoinstall's `layout` as an
  interactive default (confirmed in the code). The ISO now carries
  `/autoinstall.yaml` with everything interactive except `storage`
  (`layout: zfs`, largest disk); the destructive confirmation remains. A
  second GRUB entry, "choose storage yourself", with
  `subiquity.autoinstallpath` pointing to a file with
  `interactive-sections: ["*"]` (the standard flow). Green on both:
  `root=ZFS=rpool/ROOT/ubuntu_4s6y1t`, and LVM on the manual one.
- **grove talks to the Hive.** New user socket in the cortex,
  `/run/hive/user.sock` (0666, any local user), which only accepts
  `UserQuery`, entering/leaving anonymous mode **for its own pid**, and
  `Ping` — the components socket stays root:hive. In grove: `? question`
  (the question goes to the synapse in a priority queue that bursts of
  events don't drop; the answer goes back only to whoever asked, always
  as text, with no action), system notices at the next prompt (a service
  went down, a port conflict, disk — never suggestions, which may be about
  another user's commands) and `anon [on|off]` (the cortex ignores what
  the shell runs, including its children, by process ancestry in `/proc`;
  the anonymous session goes away when the connection closes, so that a
  reused pid doesn't inherit it). The cortex's log records who asked and
  the size, not the text. A blocking IPC client in hive-common, since
  grove has no async runtime. 5 e2e checks (red before with the old
  binaries: 5 failures), including the question asked by an unprivileged
  user. Real answer in the guest: three useful lines, one of them with a
  command made up by the 0.5B model (`systemctl list-unavailable`) — the
  quality of the answers is the limit now.

**Continued — the three open items.**

- **The package action had never worked.** The actuator runs as
  `_hive-act` and called `apt install`: in the guest, "Could not open lock
  file... are you root?" (and `NoNewPrivileges` prevents sudo). Now
  packages go through PackageKit (`pkcon`), already present on Ubuntu
  server, with a polkit rule that only allows installing, removing,
  upgrading and refreshing from trusted sources. The whitelist now
  requires a package name that is valid under Debian policy (before,
  `InstallPackage { name: "--allow-downgrades" }` got through). The lab
  found one more: with `PrivateTmp=yes`, pkcon creates the debconf socket
  in a /tmp that packagekitd doesn't see ("frontend-socket does not
  exist", code 7) — solved with `TMPDIR` in a `RuntimeDirectory` of the
  unit, keeping `PrivateTmp`.
- **To exercise this end to end** (and because it's useful): program not
  found in grove + a package of the same name available in `apt-cache` →
  grove warns and sends `CommandNotFound` → the synapse suggests "Install
  X" (a typed `InstallPackage`; name validated in the cortex, the synapse
  and the whitelist; at most one offer per package every 10 min) → an
  administrator approves in the dashboard → ZFS snapshot → pkcon installs.
  In the e2e, offline, with a local repository.
- **Dashboard for administrators who are not root.** The dashboard only
  connected to the components socket (root:hive). Now it uses the user
  socket, and the cortex only accepts it from root or from members of
  sudo/admin/wheel, checked against the groups of the account of the
  kernel-reported uid — not by the process name, and not by the `hive`
  group, which is the service accounts' group. Anyone who is not an
  administrator gets a clear message before the TUI opens (ping
  handshake). `UserAction`/`UserDismiss` are now accepted only from
  dashboards.
- **Pruning old snapshots.** `hive-zfs prune` + `hive-zfs-prune.timer`
  (daily, persistent), as root: removes `hive-*` snapshots older than
  `[zfs] prune_after_days` (14), sparing the `keep_newest` (3) newest;
  the age comes from the timestamp in the name, so third-party snapshots
  are never touched. The hive-zfs man page described commands that didn't
  exist and was rewritten.
- 7 new or changed checks (red before: 7 failures), including the restart
  flow, now approved by `druid` (sudo, not root). 72 in total.

## 2026-08-24 (continued, 8) - First real DruidOS ISO, built and booted

> **Correction (2026-09-10):** the hash below is from the first build,
> which did *not* boot (no El Torito catalog — fixed in commit `b3b6c6f`;
> the good build was `a3f92bf0…`). And the boot had never been visually
> confirmed: that only happened with the ISO Lab (entry above), which also
> showed that this ISO would install plain Ubuntu.

User's request: "how do I connect to druidos?" — after a whole session
testing individual components (via Docker on the Forge), there had never
been a really booted ISO of the project. The user chose "see/use DruidOS
for real" instead of reusing the old ISOs from February/2026 (pre-pivot,
TUI-only) or just repeating the component tests on the Forge.

**`scripts/build-iso.sh` had never been run to the end in this or any
recent session — it turned up a chain of real bugs, each one blocking the
next:**

1. The Ubuntu base ISO URL was hardcoded to `24.04` — Ubuntu only keeps
   the current point release under the numbered path (`24.04.4`, not plain
   `24.04`) and removes old versions. 404. Fixed: `BASE_POINT_RELEASE`
   parameterized.
2. `.sh` scripts arrived on the Forge with CRLF — `.gitattributes` already
   said `eol=lf`, but the local checkout on Windows (with
   `core.autocrlf=true`, which I must not touch) still produces CRLF in
   the working tree, even with a clean git blob. Fixed by normalizing on
   arrival in `test-on-forge.sh`, without touching the git config.
3. **Deepest finding**: Ubuntu 24.04 Server uses the Subiquity installer,
   which packs several squashfs images in LAYERS (to be overlaid at boot),
   not a single `filesystem.squashfs` like older (casper) ISOs. The
   script took the WRONG layer — one of the installer-only layers
   (`*.installer*.squashfs`, the Subiquity/curtin environment itself), not
   the real rootfs. Fixed: it extracts the two right layers
   (`ubuntu-server-minimal.squashfs` +
   `ubuntu-server-minimal.ubuntu-server.squashfs`) in order.
4. `unsquashfs` failed creating a fake "character device"
   (`/etc/dpkg/dpkg.cfg.d/excludes`, a build trick to skip installing
   docs/man) — `mknod` gave "Operation not permitted" even inside a
   `--privileged` Docker container with all capabilities (confirmed: it's
   not a missing capability, it's some restriction of the Forge's
   containerd/runtime environment that wasn't worth investigating more
   deeply — I tried a real VM via qemu-lab as an alternative, but it hung
   inexplicably at the guest's SSH after cloud-init finished, so I
   abandoned that path). Fixed with unsquashfs's own `-ignore-errors`.
5. `-ignore-errors` still returns exit code 2 ("non-fatal errors
   occurred"), which the script's `set -e` treated as a total failure.
   Fixed with a wrapper (`run_unsquashfs_tolerant`) that only propagates
   an error if the code is neither 0 nor 2.
6. `setup_build_dirs()` always did `rm -rf` on the whole build directory
   BEFORE the base ISO cache was checked — that is, the cache never
   worked, and every retry downloaded the ~3.2GB again. Fixed to only
   clean the extraction subdirectories, preserving `base.iso`.

**Result:** `druidos-hive-amd64.iso` (3.4GB,
sha256 `4986a8c5c55474fe5576eb498989881661f862839ebb2a8e9205bfda059d22c7`)
built successfully, with the real Hive Stack binaries and the systemd
services installed. Brought from the Forge to this machine (hash checked,
transfer intact) and booted via local QEMU.

**Discovery about the local boot:** WHPX (Windows hardware acceleration)
is compiled into the installed QEMU, but **doesn't really work on this
machine** — it fails with "WHPX: No accelerator found" /
"No space left on device" (a misleading message; it usually means Hyper-V
isn't enabled or another hypervisor has exclusive access to VT-x). It
fell back to `-accel tcg` (software emulation, functional but much
slower).

**Important:** the generated ISO is derived from the Ubuntu Server
installer (Subiquity) — booting it opens the real **interactive
installer** (partitioning, user, etc.); it doesn't drop straight into a
shell. The user is expected to drive that part manually in the QEMU
window.

---

## 2026-08-23/24 (continued, 7) - Test Ollama backend for hive-synapse (dev/test only)

Third and last item on the list of open points: `hive-synapse` only had
mock inference. The user has a Mac mini in the homelab (`10.10.1.125`,
Apple M4, 16GB, Ollama with `qwen2.5:7b`) dedicated to running LLMs, and
asked for it to be used, but only for testing (confirmed explicitly: "for
testing, yes, it can use it"). This doesn't conflict with the project's
security rule ("hive-synapse never has network access") because
`config/systemd/hive-synapse.service` already has `PrivateNetwork=yes` —
real network namespace isolation, enforced by systemd, independent of the
code. In other words: it's possible to have an optional HTTP backend that
only exists for dev (Cargo feature `ollama`, disabled by default) and
production still stays protected even in case of misconfiguration.

**Implemented:** `SynapseConfig` gained `backend` (default `"mock"`),
`ollama_url`, `ollama_model`. `hive-synapse/src/inference.rs` gained a
`Backend` enum (`Mock` | `Ollama` behind `#[cfg(feature = "ollama")]`)
and `ollama_generate()`, which calls `POST {url}/api/generate` with
`stream: false`. The response parsing (`parse_ollama_response`) was
extracted as a pure function, depending on neither the `ollama` feature
nor the network client, so that it stays testable even in builds without
that feature. If `backend = "ollama"` is configured in a build without
the feature, it falls back to the mock with a warning instead of failing.

**Discovery while configuring the Mac:** Ollama was running
(`launchd`/`homebrew.mxcl.ollama`) but listening only on
`localhost:11434` — `OLLAMA_HOST` was empty in the launchd plist (which
sets `EnvironmentVariables` explicitly, so a global `launchctl setenv`
had no effect on it). Fixed by adding `OLLAMA_HOST=0.0.0.0` directly to
the plist via `PlistBuddy` and reloading with
`launchctl bootout`/`bootstrap` — confirmed listening on `*:11434` and
reachable from the Forge.

**Real validation, partial:** `hive-synapse` with `backend = "ollama"`
connected, received a real `SuggestionRequest` (via `hive-nerve-process`
detecting a disguised dangerous command) and attempted the real HTTP
call — but Forge↔Mac mini connectivity on the homelab LAN turned out to
be unstable during the test (GETs that had worked started hanging with no
clear pattern; not even a `curl` straight from the Forge's host completed
an `/api/generate` within 2 minutes, and `ollama ps` on the Mac never
showed the model loaded, indicating that the request never even reached
the server). This is homelab network instability, not a DruidOS bug —
the error handling worked correctly ("Failed to reach Ollama backend"
logged and propagated, without hanging the process). I didn't close a
complete real generation round-trip in this session; the code and unit
tests (including the response parsing) are ready and validated, and the
end-to-end network call stays pending until the connectivity cooperates.

Tests: `unknown_backend_falls_back_to_mock`,
`parse_ollama_response_extracts_the_response_field`,
`parse_ollama_response_rejects_malformed_json`,
`parse_ollama_response_rejects_missing_response_field`. Validated
`cargo clippy -p hive-synapse --features ollama --all-targets` clean, and
the default build (without the feature) still passes normally.

---

## 2026-08-23 (continued, 6) - Confirmation of dangerous actions in hive-dashboard

Second item on the list of open points: until now, a dangerous action
approved in the dashboard (`Action::is_dangerous()` — `RestoreSnapshot`,
`DeleteSnapshot`, `RemovePackage`, `DeleteFile{permanent:true}`,
`Reboot`, `Shutdown`, `CleanSystem`) always came back rejected from
`hive-actuator`, because there was no real second-confirmation
mechanism — a single `Enter` already fired the `UserAction`, and the
actuator refused everything that arrived marked `requires_confirmation`
(fail-closed, correct, but with no way for the user to actually confirm).

**Design:** `HiveMessage::UserAction` gained a `confirmed: bool` field.
`hive-dashboard` now treats the first `Enter` key on a dangerous
suggestion as "arming" the confirmation (it sends nothing, it just marks
the line in red/bold with "(CONFIRM? press Enter again)" and changes the
status bar) — only the **second** `Enter` on the same suggestion sends
`UserAction{confirmed: true}`. Moving to another line or `Esc`/`d`
cancels the pending confirmation (instead of dismissing the notification,
if one was armed). `hive-cortex`'s `act_on_suggestion` now computes
`requires_confirmation = action.is_dangerous() && !confirmed` instead of
just `is_dangerous()`. `hive-actuator`'s logic didn't change — it still
rejects when `requires_confirmation` arrives as `true`, but now that only
actually happens for unconfirmed actions.

**Really validated on the Forge**, not just in a unit test: the
`fake_synapse` test client (already existing, see
[[e2e-test-found-2-real-bugs]]) gained `FAKE_SYNAPSE_ACTION=dangerous`
to send a `RemovePackage` suggestion instead of the default
`CleanPackageCache`, and now runs via `setpriv` as `_hive-ai` with
`exec -a hive-synapse` (the right argv[0]) — without that, this session's
own `SuggestionResponse` authentication fix rejects it, since it isn't
the real `hive-synapse`. Reading the dashboard's raw log: the 1st Enter
armed the line (red/bold, "(CONFIRM? press Enter again)", zero requests
at the actuator); the 2nd Enter sent the confirmation, the cortex
computed `requires_confirmation: false`, and the actuator processed the
action without rejecting it for confirmation (it only failed afterwards
for an apt reason inside the container, unrelated to the feature).

**Side finding, not fixed in this session:** while investigating the
earlier (non-dangerous) test I noticed that the dashboard lets you
re-approve an already approved line — `Enter` doesn't look at the
existing `outcome` before sending `UserAction` again, producing a second
request that the cortex rejects with `"UserAction for unknown notification"`
(the suggestion was already removed from `pending_suggestions` the first
time). It's not a regression from this change, it's earlier behavior;
cosmetic (it exposes nothing, just one extra warning in the log), not
tackled now.

**Finding that prevents reusing `fake_synapse` to test the suggestion
flow without disguising it as `hive-synapse`:** the `SuggestionResponse`
authentication fix from earlier today (see
[[e2e-test-found-2-real-bugs]]) now blocks `fake_synapse` itself by
default — it only works running as `_hive-ai` with `argv[0]` equal to
`hive-synapse`. An expected and correct side effect of the security fix,
documented in the example's own file.

**Process note:** syncing to the Forge via `scripts/test-on-forge.sh`
(tar) doesn't guarantee increasing mtimes — cargo, which decides whether
to recompile by mtime (not by content hash) in a default build, may think
nothing changed and skip the recompilation even with different content.
Discovered when editing `fake_synapse.rs` and seeing the old binary keep
running after a "successful" `cargo build` (`Finished in 0.09s`, with no
`Compiling`). Solution: `touch` the file before rebuilding when iterating
outside the full `check.sh` pipeline.

---

## 2026-08-23 (continued, 5) - Tackling the open points: nerve-process

After "did we achieve our goals?", the user asked to tackle the points
left open in the previous answer. Prioritized in this order:
(1) investigate why `hive-nerve-process` didn't detect the `rm -rf` in
the E2E test, (2) confirmation of dangerous actions in `hive-dashboard`,
(3) a real SLM via Ollama on the homelab's Mac mini (only for testing —
production stays without network, see [[security-audit-2026-08]]). Async
grove was left out (it was already "out of scope" in the previous plan).

**Finding 1, fixed:** `get_component_type` (`hive-cortex/src/main.rs`)
read `/proc/{pid}/comm`, which the kernel truncates to 15 bytes
(`TASK_COMM_LEN-1`). `hive-nerve-process` (19 chars) becomes a truncated
`hive-nerve-proc` — it never matches in `from_name()`, it always falls
into `Unknown`. The same problem affects `hive-nerve-journal` and
`hive-nerve-network` (also >15 chars). Confirmed empirically by reading
`/proc/PID/comm` of a real process on the Forge. Fixed: it now reads
`argv[0]` from `/proc/{pid}/cmdline` (not truncated) instead of `comm`.
Revalidated: the cortex now logs `Component type: NerveProcess` instead
of `Unknown` for the same binary.

**Finding 2, confirmed but not fixed — a real race condition in the
polling:** I tested by firing 30 fast, independent `rm -rf` against a
real `hive-nerve-process` — only **1 of the 30** was detected. A control
process (same cmdline, but a 2s lifetime via `sleep`) was caught without
trouble, confirming that the regex logic is right; the problem is purely
the 250ms poll interval on `/proc`: a command that runs and exits faster
than that (the common case for `rm`/`dd`/etc.) may never show up in a
scan. The code's own comment already anticipated this ("Uses proc
connector (if available) or polling") but only the polling was
implemented — never the netlink proc connector (`NETLINK_CONNECTOR`,
`CN_IDX_PROC`), which would deliver exec() events synchronously
regardless of the process's lifetime. Implementing that is a separate,
substantial feature (raw netlink socket, `CAP_NET_ADMIN`, different
behavior inside a container without extra privileges) — flagged to the
user, not implemented yet in this session.

---

## 2026-08-23 (continued, 4) - Real E2E test via SSH on the Forge: 2 real bugs found and fixed

User's request: "test the main flow, connect via ssh and test it" — not
just running `cargo test`, but bringing up the daemons for real (root +
the dedicated users `_hive-ai`/`_hive-sense`/`_hive-act`) in a container
on the Forge and watching the flow end to end.

**This found 2 real bugs that no unit test would catch, because none of
them runs with real Unix sockets between different users:**

1. **The cortex's socket didn't have the `hive` group.** `IpcServer::bind`
   (`crates/hive-common/src/ipc.rs`) did `chmod 0660` on the socket but
   never `chown`ed it to the `hive` group — the 0660 permission only
   works if the file's group really is `hive`. In production this "works
   by accident" because systemd's `.service` sets `Group=hive`, and the
   process inherits that gid when it creates the socket. Running
   `hive-cortex` as plain root (without that directive), the socket came
   out `root:root` and `hive-synapse`/`hive-actuator`/`hive-nerve-process`
   (group `hive`, not `root`) got `Permission denied (os error 13)` —
   confirmed when running the E2E test for the first time: the 3
   processes died at startup. **Fixed**: `IpcServer::bind` now resolves
   the `hive` group via `nix::unistd::Group::from_name` and does an
   explicit `chown` on the socket, with a warning (not a fatal error) if
   the group doesn't exist — this keeps single-user dev working with no
   extra setup.

2. **`SuggestionResponse` didn't check who sent it.** Discovered while
   writing `examples/fake_synapse.rs` (a test client that injects a
   `SuggestionResponse` with a real `Action` to exercise the
   `UserAction`→`ActionRequest` path, since the real `hive-synapse` is
   still just a mock and never attaches an `Action` to what it
   "suggests"): running as root but without being called `hive-synapse`,
   the cortex accepted and processed the suggestion anyway — the same
   kind of hole `ActionRequest` already had (earlier audit, see
   [[security-audit-2026-08]]), only at the suggestions entry point
   instead of direct execution. **Fixed**: `route()` in `router.rs` now
   checks `component_type_of(from_conn) == Some(ComponentType::Synapse)`
   before accepting (new helper `CortexState::component_type_of`);
   otherwise it rejects with `warn!`, the same pattern already used for
   `ActionRequest`. New test:
   `suggestion_response_from_a_non_synapse_connection_is_rejected`.

**Retest after the fix — everything validated for real, not just in
unit tests:**
- `hive-cortex` (root), `hive-synapse` (`_hive-ai`), `hive-actuator`
  (`_hive-act`), `hive-nerve-process` (`_hive-sense`) and `hive-dashboard`
  (root, run manually) connected and registered with the correct
  type — without a single "Permission denied".
- `fake_synapse` (root, but not called `hive-synapse`) tried to inject
  the suggestion again — the cortex correctly rejected it:
  `Rejecting SuggestionResponse from connection 5 (component type Some(Unknown), expected Synapse)`.
- `hive-dashboard` rendered correctly (confirmed by reading the process's
  raw log of escape codes: title "Hive Dashboard", border, empty state
  "(nothing yet)"/"Select a notification on the left.", status bar
  "Connected. Waiting for Hive activity..."). The capture via
  `tmux capture-pane -p` came out blank in all 4 attempts — investigated;
  it's not a dashboard bug (the raw log proves the frame was drawn
  correctly), it's a limitation of the test harness (tmux capture-pane
  vs. timing/alt-screen), not worth pursuing further.
- `hive-nerve-process` didn't detect the `rm -rf` fired directly in the
  script's shell — its observation mechanism doesn't catch that kind of
  direct trigger; it's not a regression from this session, it was already
  like that before.

**Important consequence:** the security fixes made earlier in this
session (peer-uid authentication, whitelist, etc.) had never been
exercised with really separate Unix users until this test — only in unit
tests with fake `mpsc` channels. The socket group bug shows that
"logically correct" and "works in a real deployment with separated
privileges" are different things, and only the E2E test via SSH caught
it.

**Pending items that became clear in this test, not resolved yet:**
- `crates/hive-dashboard/examples/fake_synapse.rs` exists locally and
  on the Forge but wasn't committed — it's useful as a permanent manual
  testing tool (it's the only way to exercise `UserAction`→`ActionRequest`
  with a real `Action` today, since the real `hive-synapse` doesn't attach
  an `Action` to the suggestions it "generates"), but it's also test code
  that normally wouldn't go into the main history without an explicit
  decision.
- The `druidos-e2e` container on the Forge is still running
  (`sleep infinity`) to allow more debugging if needed.

---

## 2026-08-23 (continued, 3) - hive-dashboard + UserAction→ActionRequest flow

Third part of the session (same day). After hygiene and docs, the most
substantial item was tackled: how the Hive notifies the user without a
GUI, and the `HiveMessage::UserAction` that was still a `// TODO` — that
is, even with the whitelist and authentication fixed, nothing actually
generated an `ActionRequest`.

**Finding that changed the original plan:** Grove today is synchronous
(plain `stdin().read_line()`, no tokio) and does not even run external
commands yet. Integrating notifications there would first require
rewriting it as async. We opted for a new binary, `hive-dashboard` (ratatui,
`tokio::select!` between terminal events via `crossterm::EventStream`
and the IPC socket — the same pattern as the existing daemons), instead
of touching Grove. The user runs it manually (like `top`), with no
systemd service.

**Changes in `hive-cortex`:**
- `ComponentType::Shell` renamed to `Dashboard` — the name "Shell"
  had become associated with the archived Wayland overlay.
- `SuggestionResponse` is now stored (`CortexState.pending_suggestions`)
  and becomes a `Notification` carrying the suggestions in the `actions`
  field (which already existed in `HiveMessage::Notification`, never populated).
  Fixed in passing a bug that predates this session: `forward_to_synapse`
  never recorded the originating connection (the parameter was literally
  named `_from`), so a `SuggestionResponse` could never have come back
  along the old path (`forward_to_requester`).
- `UserAction` now looks up the suggestion, and if it has an `Action`, builds
  an `ActionRequest` and dispatches it straight to the actuator (`forward_to_actuator`,
  called internally — it does not go through the network path, which was closed
  in the security fix). `requires_confirmation` comes from
  `Action::is_dangerous()` — dangerous actions are still rejected
  by the actuator (fail closed, already fixed), since there is no
  confirmation UI yet — an accepted v1 limit, not a new gap.
- `UserDismiss` now actually clears `pending_suggestions`.

`hive-common`: `Action` (and the types it uses) gained `PartialEq` —
`hive-dashboard` needs it to correlate a received `ActionResponse`
(which only carries the `Action`, not the notification/suggestion id)
with the row that is waiting for it.

16 tests in `hive-cortex` (5 new: suggestion flow, dangerous vs
non-dangerous action, unknown notification_id, dismiss) + 8 in
`hive-dashboard` (pure state logic — expanding a notification into
rows, matching an ActionResponse, list navigation, key mapping).
Everything validated on the Forge and on the real GitHub CI before the push
(commit `2ba745f`).

Docs updated: `CLAUDE.md` (the two open questions this
resolves), `docs/architecture.md`, `docs/HIVE-STACK.md`,
`docs/user-guide.md`, `debian/control`/`rules` (packages the new binary).

### Open items
- Interactive confirmation of dangerous actions inside the dashboard (v2).
- Grove is still synchronous and without external command execution — an
  incidental finding of this session, not addressed (it was not asked for).
- `pending_suggestions` has no time-based expiry (same level as the
  already existing `pending_requests`).

---

## 2026-08-23 (continued) - Fixing the security findings + hygiene

Same day, a direct continuation of the entry below. The 5 security
findings listed in the previous entry as "none fixed" **were
all fixed** in this part of the session (commit `6fe1144`), validated
by the Forge loop and then by the real GitHub CI:

1. **Authentication by real uid**: `hive-cortex` now cross-checks the
   self-declared component type (`/proc/pid/comm`) against the connection's
   real uid (`nix::unistd::User::from_uid`), matching it against the
   expected user in `config/systemd/hive-*.service`. A mismatch downgrades it to
   `Unknown`. `crates/hive-cortex/src/main.rs`.
2. **External `ActionRequest` rejected**: `router.rs` no longer forwards
   an `ActionRequest` coming from any connection — only cortex should generate
   that message (documented protocol), and today it does not even do so yet (`UserAction`
   is still a TODO). `forward_to_actuator` was left with `#[allow(dead_code)]`
   for when that flow is built.
3. **Confirmation fails closed**: `hive-actuator` rejects actions that
   require confirmation instead of executing them anyway (there is no UI to
   really confirm yet).
4-5. **Whitelist rewritten**: `crates/hive-actuator/src/whitelist.rs`
   now corresponds 1:1 to the real `Action` enum (the old `whitelist.toml`
   referenced action types that do not exist in the code). Exact
   matching of command+positional args (closed the `iptables` bypass via
   `"ip"`), glob `*` for paths/services/packages, the default is to deny everything
   (before, it was a hardcoded "safe" list that could diverge from the real
   file). Rate limit per action type, in addition to the existing global one.

Explicitly out of scope: the `UserAction`→`ActionRequest` flow itself
(a new feature, not a fix), granular authorization per message type
beyond `ActionRequest`.

### Quick hygiene

- Removed 20 loose files at the root (untracked): debug junk (`nul`,
  empty/obsolete logs) and scripts that pointed to `dist/v0.4-fb`
  (archived) or to old build VMs (replaced by the Forge).
  Kept `kill-qemu.ps1`/`kill-all-qemu.ps1` (generic).
- SSH key in `qemu-workspace/keys/` confirmed as already covered by
  `.gitignore` (not moved — it is the workspace the `qemu-lab` MCP expects).
- `installer/` (TUI installer in ratatui/crossterm — already aligned with the
  pivot) was never in the Cargo workspace, never compiled/linted/tested.
  Added; fixed the 4 real clippy warnings from the first
  pass.

Memory `security-audit-2026-08` updated to reflect that the 5
findings are fixed.

---

## 2026-08-23 - Audit, test pipeline and new coverage

### Project audit

Security findings in the Hive Stack (none fixed in this part of the
session — fixed later the same day, see the entry above):

- `hive-cortex` authenticates components by `/proc/{pid}/comm`
  (`get_component_type`), not by the uid of the peer credential it already collects —
  any local process can impersonate another component just by naming
  the binary.
- `router.rs` forwards `ActionRequest` from **any** connection straight to the
  actuator, without checking whether it came from the cortex itself.
- Action confirmation (`requires_confirmation`) is a `// TODO: Handle
  confirmation requirement` that does nothing — it executes anyway
  (`hive-actuator/src/main.rs`).
- `config/hive/whitelist.toml` (rich schema, `[[actions]]`) is incompatible
  with the Rust struct that reads it (`WhitelistConfig`) — it loads almost empty and
  treats packages as "allow all" by default.
- Command matching by string prefix in the whitelist lets
  `iptables` through via `"ip"`, and `find`/`git` without argument restrictions
  allow arbitrary exec (e.g. `git -c core.fsmonitor=...`).

Hygiene findings:

- `qemu-workspace/keys/id_ed25519` (private SSH key) sitting in the working
  tree, untracked but not ignored.
- `.gitignore` did not cover `dist/`, `output/`, `qemu-workspace/` —
  fixed in this session (see below, it almost sent 54GB to the Forge).
- Several loose files at the root (`nul`, `print.png`, `*.log`, `*.ps1`)
  not yet dealt with.

### Test pipeline: CI fixed + loop on the Forge

`.github/workflows/ci.yml` ("CI": fmt/clippy/test/build/audit/docs) had never
run even once — it only triggered on push to `main`/`develop`, and
all the work happens on `claude/**` branches. Fixed the trigger.
On the first real run, a second pre-existing bug showed up: the action
`dtolnay/rust-action@stable` does not exist (it is `dtolnay/rust-toolchain@stable`)
— every job failed at "Set up job". Fixed.

`rust-build.yml` ("Rust Components Build") was removed: it did trigger on
`claude/**`, but the paths filter (`bark/**`, `spore/**`,
`grove/**`) dates from before the Hive Stack joined the workspace — it never tested
any `hive-*` crate, which is where most of the code lives.

Created `scripts/check.sh` (fmt --check + clippy -D warnings + test
--workspace, the same command the CI runs) and, since Windows does not
cross-compile the crates that pull in `ring`/`openssl-sys` (it lacks an
`x86_64-linux-gnu-gcc`), a local loop via the Forge (the homelab's Docker
server, `10.10.1.40`, SSH alias `forge`): `scripts/test-on-forge.sh`
packages the working tree (`git ls-files`, which also picks up what has not
been committed yet) and runs `check.sh` there inside a container
(`scripts/forge-test.Dockerfile`, image `rust:1-bookworm` +
rustfmt/clippy/libssl-dev). Nothing compiles locally on Windows; the cargo
registry and `target/` persist on the Forge between runs.

**Near-incident:** `.gitignore` never covering `dist/`/`output/`/
`qemu-workspace/` meant that `git ls-files --others --exclude-standard`
was going to send ~54GB (ISOs, qcow2 disks, and the private SSH key) to the Forge on the
first sync. Caught before it completed, the hung process killed, 41GB
of partial files cleaned off the Forge (via a root container, since the files had become
root-owned by the build inside the container), `.gitignore` fixed.

### Technical debt: clippy backlog cleared

The workspace had never passed `cargo clippy --workspace --all-targets
-- -D warnings` end to end. Using the Forge loop, ~20 real warnings
in 8 crates showed up (and were fixed): unused imports,
redundant closures, `derivable_impls` (2x manual `impl Default` that
becomes `#[derive(Default)]`), `useless_vec!`, `manual_strip`,
`single_match`/`collapsible_match`, `needless_return`, an inherent
`to_string()` method became `impl Display`, a `History::next()` renamed
to `next_entry()` (it clashed with the name of the `Iterator` trait's method),
and `#[allow(dead_code)]` with a one-line justification for the fields/methods
that are genuine scaffolding not yet wired up (`FsEvent::PermissionChanged`
and its `description`/`severity` methods, `recent_paths`,
`create_pre_operation_snapshot`, and the `pid`/`uid`/`config` fields of
`hive-cortex` — these last ones are the same as in the security audit;
the `allow` only silences the lint, it does not change the behavior).

### New test coverage

`hive-cortex/src/router.rs` (282 lines, 0 tests before — it is the heart of
message routing) gained 7 tests that build a real `CortexState`/
`SharedState` and fake components via `mpsc` channels (the same pattern
already used in the IPC test of `hive-common`, just without a real socket):
Ping/Pong, `CommandObserved` → synapse, suppression in anonymous mode,
`PortConflict` → synapse+shell, `ActionRequest` → actuator, and
`ActionResponse` going back to the original requester via `request_id`.

`hive-actuator/src/main.rs` (817 lines, 0 tests) gained 4 tests for the
`RateLimiter` (rate window) and `is_destructive_action`.

`hive-cortex/src/main.rs` gained 2 tests for `ComponentType::from_name`.

Left out on purpose: integration tests that would exercise the router's
authorization gap — they would be born red without fixing the bug
first, so they are left for the dedicated security session.

### Commits of this session (on top of `897cd44`)

1. `fb49bac` refactor: redefine project target to TUI-only, archive GUI track
2. `8183cf5` style: apply cargo fmt across the Hive Stack
3. `bb5846e` ci: fix test pipeline triggers, drop redundant workflow
4. `539e918` fix: correct dtolnay/rust-toolchain action name in ci.yml
5. `4f22e3b` fix: clear the clippy -D warnings backlog across the workspace
6. `cd9c2c0` feat: add Forge-based test loop (native Linux, no WSL/cross-compile)
7. `92e5fae` test: add unit coverage for hive-cortex routing and hive-actuator

### Open items (status at the end of the day — see the two entries above)

- ~~Security fixes from the audit~~ — **fixed**, see the entry
  "Fixing the security findings + hygiene" above.
- `docs/architecture.md`, `docs/security-model.md`, `docs/user-guide.md`,
  `scripts/build-iso.sh`, `scripts/build-image.sh`, `installer/src/main.rs`
  (the `enable_hive`/`install_desktop` options, specifically — the crate
  itself has compiled/linted since the hygiene cleanup), `.github/workflows/release.yml`
  still describe the Hyprland/Wayland desktop as current — not updated
  in the TUI-only pivot (out of scope at the time).
- ~~Repository hygiene: loose files at the root~~ — **cleaned up** (see the
  entry above). Still pending: `.mcp.json`/`config/hive/config.toml`
  untracked, undecided whether they should be versioned.
- The Hive's notification mechanism without a GUI still undefined (see the
  pivot entry, below).

---

## 2026-08-23 - Target redefinition: TUI-only (no GUI)

### Decision

The project had two CPU-only graphics bets in parallel, neither
integrated end to end:
1. `bark` + `spore` — a direct framebuffer engine (mmap on `/dev/fb0`),
   being debugged in the previous session (v0.4-fb, mmap segfault).
2. `hive-shell` + `hive-dock` + `hive-term` — a Wayland/Hyprland desktop
   rendering via Mesa+LLVMpipe, which never got as far as having a systemd service.

Decision: **abandon the GUI, focus 100% on terminal/TUI**, with `grove` as the
main interface.

### Actions

- Moved to `archive/` (outside the Cargo workspace, git history preserved
  via `git mv`): `bark/`, `spore/`, `crates/hive-shell/`, `crates/hive-dock/`,
  `crates/hive-term/`, `examples/fb-test.rs`, `assets/`,
  `config/hyprland/`, `config/waybar/`, `config/applications/*.desktop`.
- Root `Cargo.toml`: removed the 5 graphical crates from `members` and the
  `memmap2`/`input-linux` dependencies (their only consumers were `bark`).
- `grove/Cargo.toml`: removed the `bark` dependency (it was not used in the code).
- `debian/control`: removed the `druidos-hive-desktop` package and the
  build-deps `libwayland-dev`/`libxkbcommon-dev`.
- `CLAUDE.md`, `docs/HIVE-STACK.md`, `STATUS.md`: updated to reflect
  the new scope.

### Open items

Without `hive-shell`, it is not yet defined how `hive-cortex` should deliver
notifications/suggestions to the user (inline in Grove? a separate TUI panel?).
See "Open Questions" in `CLAUDE.md`. `ComponentType::Shell` in
`hive-cortex/src/router.rs` remains in the code, with no registered consumer.

Uncommitted framebuffer fixes (`archive/bark/src/framebuffer.rs`)
were preserved in the archived code; they only left the active build.

---

## 2026-02-20 - v0.4 Framebuffer Development

### Goal
Validate bark (HAL) and spore (2D rendering engine) to implement a GUI without a GPU.

### Achievements

#### 1. Framebuffer working
- `/dev/fb0` appears with the parameter `vga=0x31B`
- Resolution: 1280x1024 @ 24bpp
- fb-test opens the framebuffer successfully

#### 2. Bugs identified in `bark/src/framebuffer.rs`

**Bug 1: mmap without an explicit size**
```rust
// BEFORE (does not work for device files):
MmapMut::map_mut(&file)

// AFTER (fix applied):
memmap2::MmapOptions::new()
    .len(size)
    .map_mut(&file)
```

**Bug 2: flush() assumed 32bpp**
The method was rewritten to support 24bpp, 32bpp and 16bpp.

#### 3. DruidOS v0.4-fb created
- `dist/v0.4-fb/bonsai-kernel` (15MB)
- `dist/v0.4-fb/bonsai-initramfs.img` (2.6MB) - without SLM

### Current problem
The fixes are in the code but **not compiled**. The current fb-test segfaults.

### Broken build environment
- Ubuntu VM: kernel panic "IO-APIC + timer doesn't work"
- WHPX: "No space left on device"
- WSL: available but with no distribution

### Pending solution
Install WSL Ubuntu:
```powershell
wsl --install -d Ubuntu
```
Then run `build-fb-test.sh`

### Scripts created
- `run-fb.ps1` - Starts DruidOS with the framebuffer
- `kill-all-qemu.ps1` - Kills all QEMU processes
- `build-fb-test.sh` - Compiles fb-test (Linux)

### QEMU parameters for the framebuffer
```
-vga std -append "vga=0x31B noapic nolapic console=tty0"
```

---

## 2026-02-19 - Development session

### Environment set up
- **QEMU**: 10.2.0 installed on Windows
- **MCP qemu-lab**: Working to control VMs
- **Ubuntu 24.04 VM**: Running via nested virtualization (Proxmox → Windows → QEMU)
- **Rust**: 1.93.1 installed both on Windows and in the VM

### Achievements

#### 1. MCP QEMU Lab operational
- Ubuntu 24.04 cloud image VM booting successfully
- SSH working (with the key in `qemu-workspace/keys/id_ed25519`)
- Disk expanded from 2.4GB to 11GB to make room for compiling

#### 2. Unified Rust workspace
- Added 13 `hive-*` crates to the workspace
- Workspace dependencies updated (bincode, toml, uuid, dirs, regex, which, etc.)
- Cross-check works on Windows for the target `x86_64-unknown-linux-gnu`

#### 3. Full build on the Ubuntu VM
All 13 Hive Stack binaries compiled in release:

| Binary | Size | Description |
|--------|------|-------------|
| hive-cortex | 2.2M | Central orchestrator |
| hive-synapse | 2.2M | AI engine (Candle + tokenizers) |
| hive-actuator | 2.3M | Action executor |
| hive-apt | 1.1M | Smart APT wrapper |
| hive-zfs | 2.2M | ZFS integration |
| hive-nerve-process | 2.7M | Process monitor |
| hive-nerve-journal | 2.8M | Log monitor (journald) |
| hive-nerve-network | 2.1M | Network monitor |
| hive-nerve-fs | 2.0M | Filesystem monitor |
| hive-shell | 2.2M | Desktop overlay |
| hive-dock | 2.0M | Dock bar |
| hive-term | 2.2M | Terminal emulator |

**Total: ~25MB** (release, LTO, stripped)

### Problems found and solutions

#### SSH timeout in the MCP
- **Problem**: The MCP's `guest_exec` timed out
- **Solution**: Use SSH directly with the key in `qemu-workspace/keys/id_ed25519`

#### Small disk in the VM
- **Problem**: The cloud image has only 2.4GB, Rust needs more
- **Solution**: `qemu-img resize disk-overlay.qcow2 +8G` + `resize2fs`

#### Cross-compiling on Windows
- **Problem**: MSVC not installed, wrong link.exe
- **Solution**: GNU toolchain (`stable-x86_64-pc-windows-gnu`)
- **Limitation**: hive-synapse needs OpenSSL/a full cross-compiler

### Build workflow

```bash
# On Windows (cross-check only):
cargo check -p hive-common --target x86_64-unknown-linux-gnu

# On the Ubuntu VM (full build):
ssh -i qemu-workspace/keys/id_ed25519 -p PORT lab@127.0.0.1
cd ~/druidos
source ~/.cargo/env
cargo build --workspace --release

# Copy the binaries back:
scp -i qemu-workspace/keys/id_ed25519 -P PORT lab@127.0.0.1:~/druidos/target/release/hive-* target/release/
```

### ✅ Hive Stack tested
- hive-cortex running successfully
- IPC socket created at `/run/hive/cortex.sock`
- Full config at `/etc/hive/config.toml`

### Next steps
1. [x] ~~Create the DruidOS ISO~~ ✅ Done!
2. [x] ~~Test communication between components~~ ✅ Working!
3. [ ] Integrate the SLM model

---

## 2026-02-19 - Session 2: Hive Stack complete

### ✅ DruidOS ISO created

- **File**: `output/druidos-0.1.0-amd64.iso` (1.5GB)
- **Base**: Ubuntu 24.04 minimal via debootstrap
- **Tools**: grub-mkrescue, squashfs-tools
- **Status**: GRUB works, the kernel starts (slow under TCG/software emulation)

### ✅ Hive Stack backend complete

7 components running simultaneously with working IPC:

| Component | PID | Connection | Status |
|-----------|-----|------------|--------|
| hive-cortex | 11751 | - | Orchestrator active |
| hive-nerve-process | 11816 | 1 | Intercepting rm,chmod,dd |
| hive-nerve-journal | 11924 | 2 | Monitoring logs |
| hive-nerve-network | 11930 | 3 | Monitoring ports |
| hive-nerve-fs | 12050 | 4 | Watching /etc,/var/log,/home |
| hive-actuator | 12049 | 5 | Ready (0 whitelisted actions) |
| hive-synapse | 12163 | 6 | Mock inference (no model) |

### ✅ Command interception tested

```
[INFO] Detected dangerous command 'rm': rm -rf /home/lab/...
```

nerve-process detects dangerous patterns and sends them to the cortex via IPC.

### Desktop components (pending)

- hive-shell, hive-dock, hive-term require Wayland
- They cannot be tested in the VM without a graphical environment

### Next steps
1. [ ] Download the SLM model (Qwen 2.5 0.5B GGUF)
2. [ ] Test real inference in synapse
3. [ ] Set up Hyprland on the ISO

---

## Technical notes

### Development VM
- **ID**: vm-ubuntu-test-60eefea9
- **SSH Port**: Dynamic (check with `vm_status`)
- **User**: lab
- **SSH key**: `qemu-workspace/keys/id_ed25519`

### File structure
```
druidos/
├── target/release/       # Linux binaries (copied from the VM)
│   ├── hive-cortex
│   ├── hive-synapse
│   └── ...
├── crates/               # Source code
│   ├── hive-common/
│   ├── hive-cortex/
│   └── ...
├── qemu-workspace/       # VMs and QEMU artifacts
│   ├── keys/             # SSH keys
│   ├── vms/              # VM disks
│   └── logs/             # QEMU logs
└── scripts/              # Build scripts
    └── build-iso.sh      # ISO generator
```
