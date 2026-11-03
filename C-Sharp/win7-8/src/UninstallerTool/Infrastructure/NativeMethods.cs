using System;
using System.Runtime.InteropServices;

namespace UninstallerTool.Infrastructure
{
    internal static class NativeMethods
    {
        public const int DwmUseImmersiveDarkMode = 20;
        public const int DwmUseImmersiveDarkModeLegacy = 19;
        public const int MoveFileDelayUntilReboot = 0x4;

        private const uint SnapshotProcesses = 0x00000002;

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        public struct ProcessEntry
        {
            public uint Size;
            public uint Usage;
            public uint ProcessId;
            public IntPtr DefaultHeapId;
            public uint ModuleId;
            public uint Threads;
            public uint ParentProcessId;
            public int BasePriority;
            public uint Flags;

            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)]
            public string Executable;
        }

        [DllImport("dwmapi.dll", SetLastError = true)]
        private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attribute, ref int value, int size);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool MoveFileEx(string existingFileName, string newFileName, int flags);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr CreateToolhelp32Snapshot(uint flags, uint processId);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool Process32First(IntPtr snapshot, ref ProcessEntry entry);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool Process32Next(IntPtr snapshot, ref ProcessEntry entry);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);

        [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern uint PrivateExtractIcons(
            string fileName,
            int iconIndex,
            int iconWidth,
            int iconHeight,
            IntPtr[] icons,
            uint[] iconIds,
            uint iconCount,
            uint flags);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool DestroyIcon(IntPtr icon);

        public static void SetDarkTitleBar(IntPtr handle, bool dark)
        {
            if (handle == IntPtr.Zero)
            {
                return;
            }

            var value = dark ? 1 : 0;
            try
            {
                if (DwmSetWindowAttribute(handle, DwmUseImmersiveDarkMode, ref value, sizeof(int)) == 0)
                {
                    return;
                }

                DwmSetWindowAttribute(handle, DwmUseImmersiveDarkModeLegacy, ref value, sizeof(int));
            }
            catch (DllNotFoundException)
            {
            }
            catch (EntryPointNotFoundException)
            {
            }
        }

        public static bool ScheduleDelete(string path)
        {
            return MoveFileEx(path, null, MoveFileDelayUntilReboot);
        }

        public static IntPtr ExtractIcon(string path, int index, int size)
        {
            var icons = new IntPtr[1];
            var ids = new uint[1];
            var count = PrivateExtractIcons(path, index, size, size, icons, ids, 1, 0);
            return count == 0 ? IntPtr.Zero : icons[0];
        }

        public static void ReleaseIcon(IntPtr icon)
        {
            if (icon != IntPtr.Zero)
            {
                DestroyIcon(icon);
            }
        }

        public static System.Collections.Generic.List<ProcessEntry> EnumerateProcesses()
        {
            var entries = new System.Collections.Generic.List<ProcessEntry>();
            var snapshot = CreateToolhelp32Snapshot(SnapshotProcesses, 0);
            if (snapshot == IntPtr.Zero || snapshot == new IntPtr(-1))
            {
                return entries;
            }

            try
            {
                var entry = new ProcessEntry { Size = (uint)Marshal.SizeOf(typeof(ProcessEntry)) };
                if (!Process32First(snapshot, ref entry))
                {
                    return entries;
                }

                do
                {
                    entries.Add(entry);
                    entry.Size = (uint)Marshal.SizeOf(typeof(ProcessEntry));
                }
                while (Process32Next(snapshot, ref entry));
            }
            finally
            {
                CloseHandle(snapshot);
            }

            return entries;
        }
    }
}
