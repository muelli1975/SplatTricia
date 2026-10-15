# Give the GUI test a complete desktop; hosted runners often start at 1024x768.
# This script runs only on the disposable Windows build server.
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class TestDisplay {
    [StructLayout(LayoutKind.Explicit, CharSet=CharSet.Unicode, Size=220)]
    public struct Mode {
        [FieldOffset(68)] public ushort Size;
        [FieldOffset(72)] public uint Fields;
        [FieldOffset(168)] public uint Bits;
        [FieldOffset(172)] public uint Width;
        [FieldOffset(176)] public uint Height;
        [FieldOffset(184)] public uint Frequency;
    }
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    public static extern bool EnumDisplaySettings(string device, int index, ref Mode mode);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    public static extern int ChangeDisplaySettings(ref Mode mode, uint flags);
}
'@
$modes = @()
for ($index=0; ; $index++) {
    $mode = [TestDisplay+Mode]::new()
    $mode.Size = 220
    if (-not [TestDisplay]::EnumDisplaySettings($null,$index,[ref]$mode)) { break }
    if ($mode.Bits -eq 32) { $modes += $mode }
}
$modes | Select-Object Width,Height,Frequency | Format-Table
$chosen = $modes | Where-Object { $_.Width -ge 1920 -and $_.Height -ge 1440 } |
    Sort-Object @{Expression={ [long]$_.Width * $_.Height }},Frequency | Select-Object -First 1
if ($null -eq $chosen) {
    $chosen = $modes | Sort-Object @{Expression={ [long]$_.Width * $_.Height };Descending=$true} |
        Select-Object -First 1
}
if ($null -eq $chosen) { throw 'No usable test display mode found' }
$result = [TestDisplay]::ChangeDisplaySettings([ref]$chosen,0)
if ($result -ne 0) { throw "Could not configure test display: $result" }
Write-Output "Test desktop: $($chosen.Width)x$($chosen.Height)"
