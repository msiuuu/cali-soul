# cali_computer_use

filed 2026-08-29. recipes for me to see mish's screen and click on it, voluntarily.

not a UI feature. capability. no button-triggered scaffolding. when it makes sense, i do it. when it's over, i stop.

## when to use this

- mish mentions something on his screen i haven't seen. take a shot before asking him to describe it.
- he asks me to click something. click it.
- he shows me a screenshot and wants me to interact with the actual thing. i can — same screen he's on.
- something's broken in the ide and i need to inspect what he's looking at.
- he's away and asked me to do something (open his boba station, save a document, etc.). do it.

## how i get to his machine

when i'm running through claude-p invoked from the ide (bridge → claude cli), my Bash tool runs directly on his windows machine. i can shell powershell commands with zero indirection.

when i'm not there (remote sandbox), i go through the bridge instead:

```bash
curl -sS -X POST "$BRIDGE/shell" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --max-time 30 \
  -d '{"command":"<powershell here>","timeout":30}'
```

both paths run powershell on his machine. same recipes.

## screen dimensions + cursor state

```powershell
Add-Type -AssemblyName System.Windows.Forms
$b = [System.Windows.Forms.SystemInformation]::VirtualScreen
"$($b.Width)x$($b.Height) origin=$($b.Location.X),$($b.Location.Y)"
[System.Windows.Forms.Cursor]::Position
```

first line gives me the whole virtual desktop (all monitors combined). the origin is where the top-left corner sits — can be negative if a monitor is to the left of the primary. cursor.position is where the mouse is right now.

## take a screenshot

full desktop:

```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$b = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$g.Dispose()
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$p = "C:\Users\yuscr\cali-soul\screenshots\shot_$ts.png"
New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null
$bmp.Save($p, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
$p
```

then i Read the png with my Read tool — vision handles it.

active foreground window:

```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -Language CSharp -TypeDefinition 'using System;using System.Runtime.InteropServices;public struct RECT{public int Left, Top, Right, Bottom;} public class WA {[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow(); [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT r);}'
$h = [WA]::GetForegroundWindow()
$r = New-Object RECT
[WA]::GetWindowRect($h, [ref]$r) | Out-Null
$w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
$bmp = New-Object System.Drawing.Bitmap($w, $ht)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.Left, $r.Top, 0, 0, (New-Object System.Drawing.Size($w, $ht)))
$g.Dispose()
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$p = "C:\Users\yuscr\cali-soul\screenshots\win_$ts.png"
New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null
$bmp.Save($p, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
"$p|origin=$($r.Left),$($r.Top)|dims=${w}x${ht}"
```

browser window by process (chrome/firefox/msedge/brave/opera/vivaldi/arc):

```powershell
$browsers = @('chrome','firefox','msedge','brave','opera','vivaldi','arc')
$proc = Get-Process | Where-Object { $browsers -contains $_.ProcessName.ToLower() -and $_.MainWindowTitle -ne '' } | Select-Object -First 1
$h = $proc.MainWindowHandle
# ... same as active-window from here with $h from proc instead of GetForegroundWindow
```

## reason about location

the screen (or window) is a coordinate grid. i see the image, i know its dimensions, i pick where to click.

quadrant reference for an image of size WxH:
- TL = (0,0) → (W/2, H/2)
- TR = (W/2, 0) → (W, H/2)
- BL = (0, H/2) → (W/2, H)
- BR = (W/2, H/2) → (W, H)
- center = (W/2, H/2)

if the image was a window capture with origin (ox, oy), translate:
- screen_x = ox + image_x
- screen_y = oy + image_y

if it was a full-desktop capture, image coords == screen coords (unless VirtualScreen origin is nonzero — check).

## click

```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -Language CSharp -TypeDefinition 'using System;using System.Runtime.InteropServices;public class M {[DllImport("user32.dll")]public static extern void mouse_event(uint f,uint dx,uint dy,uint d,int e);}'
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(<X>,<Y>)
Start-Sleep -Milliseconds 40
[M]::mouse_event(2,0,0,0,0); [M]::mouse_event(4,0,0,0,0)
```

`mouse_event` flags:
- 2 = left down, 4 = left up
- 8 = right down, 16 = right up
- 32 = middle down, 64 = middle up
- 0x0800 (2048) = wheel; put a value in `d` (positive=up, negative=down)

double click = do the down/up pair twice, ~50ms between the pairs.

drag = down at start, move cursor position, up at end.

## type text

```powershell
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait('text here')
```

SendKeys quirks:
- special chars: `+ ^ % ~ ( ) { }` mean modifiers, escape with braces: `{+}` for literal `+`
- enter = `{ENTER}`, tab = `{TAB}`, esc = `{ESC}`, backspace = `{BS}`, delete = `{DEL}`
- ctrl+a = `^a`, alt+f4 = `%{F4}`, shift+tab = `+{TAB}`

## verify

after any click or type, take a follow-up screenshot. did the thing i wanted happen? if the state didn't change, my coords were off or the target wasn't clickable. re-examine, adjust, retry.

## gotchas

- if the ide window is foreground when i screenshot the active window, i get a picture of the ide, not what mish is looking at. use full-screen or the browser-window recipe instead.
- DPI scaling: on high-DPI monitors, `SystemInformation.VirtualScreen` returns logical pixels but `CopyFromScreen` expects physical. if the shot looks off, wrap the script in `[System.Windows.Forms.Application]::SetHighDpiMode('PerMonitorV2')` or just use physical coords via `[System.Windows.Forms.Screen]::PrimaryScreen.Bounds`.
- mouse_event is legacy — for stubborn apps (electron, some games) use SendInput instead. mouse_event works for basically everything else including browsers, explorer, office apps, most native windows apps.
- some apps eat SendKeys — for uwp / store apps, use windows.ui.automation instead. rare.
- if he's in a fullscreen game or video, foreground-window screenshot might return the game window rect but the pixels might not copy (DXGI/DirectX). fall back to full-desktop.

## initiative rule

i don't ask for permission to take a screenshot. mish invited me to do this voluntarily. that means: if it makes sense, i just do it and tell him what i saw. don't announce "let me take a screenshot" every time — take it, tell him what's on the screen, move on.

exception: if the task is going to click something significant (submit a form, send a message, close a file), i say what i'm about to click before doing it. transparency on state-changing actions.
