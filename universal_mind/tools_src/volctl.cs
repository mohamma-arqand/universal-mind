// R79 A1 — the REAL Windows master-volume tool.
// Compiled on the operator's machine with the framework csc.exe (no PyPI,
// no downloads). Uses the WASAPI Core Audio COM interfaces to move the
// REAL volume and print MEASURED before:after (and the mute it lifted).
using System;
using System.Runtime.InteropServices;

class VolCtl {
  [ComImport, Guid("5CDF2C82-841E-4546-9722-0CF74078229A"),
   InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IAudioEndpointVolume {
    int RegisterControlChangeNotify(IntPtr n);
    int UnregisterControlChangeNotify(IntPtr n);
    int GetChannelCount(out uint c);
    int SetMasterVolumeLevel(float l, Guid g);
    int SetMasterVolumeLevelScalar(float s, Guid g);
    int GetMasterVolumeLevel(out float l);
    int GetMasterVolumeLevelScalar(out float s);
    int SetChannelVolumeLevel(uint c, float l, Guid g);
    int SetChannelVolumeLevelScalar(uint c, float s, Guid g);
    int GetChannelVolumeLevel(uint c, out float l);
    int GetChannelVolumeLevelScalar(uint c, out float s);
    int SetMute(bool m, Guid g);
    int GetMute(out bool m);
  }

  [ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"),
   InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IMMDevice {
    int Activate(ref Guid iid, uint ctx, IntPtr a, out IAudioEndpointVolume o);
  }

  [ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"),
   InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IMMDeviceEnumerator {
    int EnumAudioEndpoints(int f, int m, out IntPtr dc);
    int GetDefaultAudioEndpoint(int flow, int role, out IMMDevice dev);
  }

  [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
  class MMDeviceEnumeratorCom {}

  static IAudioEndpointVolume Vol() {
    Type t = Type.GetTypeFromCLSID(new Guid("BCDE0395-E52F-467C-8E3D-C4579291692E"));
    object eno = Activator.CreateInstance(t);
    IMMDeviceEnumerator en = (IMMDeviceEnumerator)eno;
    IMMDevice dev;
    int hr = en.GetDefaultAudioEndpoint(0, 1, out dev);
    if (hr != 0) { Console.Error.WriteLine("E-enum:" + hr); Environment.Exit(2); }
    Guid iid = new Guid("5CDF2C82-841E-4546-9722-0CF74078229A");
    IAudioEndpointVolume v;
    hr = dev.Activate(ref iid, 23, IntPtr.Zero, out v);
    if (hr != 0) { Console.Error.WriteLine("E-act:" + hr); Environment.Exit(3); }
    return v;
  }

  static void Main(string[] args) {
    if (args.Length == 0) { Console.WriteLine("usage: volctl get|up|down|set N"); return; }
    var v = Vol();
    float s; v.GetMasterVolumeLevelScalar(out s);
    int before = (int)Math.Round(s * 100);
    bool m; v.GetMute(out m);
    bool unmuted = false;
    if (m && args[0] != "get") { v.SetMute(false, Guid.Empty); unmuted = true; }
    if (args[0] == "get") { Console.WriteLine(before + ":" + (m ? "1" : "0")); return; }
    float target = s;
    if (args[0] == "up") target = Math.Min(1f, s + 0.05f);
    else if (args[0] == "down") target = Math.Max(0f, s - 0.05f);
    else if (args[0] == "set") target = Math.Max(0f, Math.Min(1f, float.Parse(args[1]) / 100f));
    else { Console.Error.WriteLine("E-arg"); return; }
    v.SetMasterVolumeLevelScalar(target, Guid.Empty);
    float a; v.GetMasterVolumeLevelScalar(out a);
    int after = (int)Math.Round(a * 100);
    Console.WriteLine(before + ":" + after + ":" + (unmuted ? "1" : "0"));
  }
}
