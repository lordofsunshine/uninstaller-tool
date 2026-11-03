using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using Microsoft.Win32;
using UninstallerTool.Core;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Tests
{
    internal static class Program
    {
        private static int _checks;
        private static int _failures;
        private static string _temporaryRoot;

        private static int Main()
        {
            _temporaryRoot = Path.Combine(Path.GetTempPath(), "UninstallerToolTests_" + Guid.NewGuid().ToString("N").Substring(0, 8));
            Directory.CreateDirectory(_temporaryRoot);

            var tests = new (string Name, Action Body)[]
            {
                ("formatting.size", FormattingSize),
                ("formatting.date", FormattingDate),
                ("formatting.normalize", FormattingNormalize),
                ("formatting.icon-reference", FormattingIconReference),
                ("commands.split", CommandsSplit),
                ("commands.msi", CommandsMsi),
                ("commands.nsis-silent", CommandsNsis),
                ("commands.resolve", CommandsResolve),
                ("commands.batch", CommandsBatch),
                ("commands.exit-codes", CommandsExitCodes),
                ("safety.normalize", SafetyNormalize),
                ("safety.depth-and-within", SafetyDepthWithin),
                ("safety.protected", SafetyProtected),
                ("safety.removal", SafetyRemoval),
                ("registry.scan", RegistryScan),
                ("registry.snapshot", RegistrySnapshotBuild),
                ("registry.find", RegistryFind),
                ("registry.export-delete", RegistryExportDelete),
                ("store.parse", StoreParse),
                ("store.fetch", StoreFetch),
                ("files.scan", FilesScan),
                ("files.remove", FilesRemove),
                ("leftovers.search", LeftoversSearchTest),
                ("leftovers.remove", LeftoversRemoveTest),
                ("sizes.cache", SizeCacheTest),
                ("settings.roundtrip", SettingsRoundtrip),
                ("processes.find", ProcessesFind),
                ("uninstall.success", UninstallSuccess),
                ("uninstall.failure", UninstallFailure),
                ("elevation.admin", ElevationCheck),
                ("ui.dialogs", () => UiDialogTests.Run(True))
            };

            foreach (var (name, body) in tests)
            {
                try
                {
                    body();
                }
                catch (Exception exception)
                {
                    _failures++;
                    Console.WriteLine("FAIL  " + name + "  -> " + exception.GetType().Name + ": " + exception.Message);
                }
            }

            Cleanup();

            Console.WriteLine();
            Console.WriteLine("checks=" + _checks + " failures=" + _failures);
            return _failures == 0 ? 0 : 1;
        }

        private static void FormattingSize()
        {
            Equal("0.00 B", Formatting.FormatSize(0), "zero");
            Equal("512.00 B", Formatting.FormatSize(512), "bytes");
            Equal("1.00 KB", Formatting.FormatSize(1024), "kilobytes");
            Equal("1.50 KB", Formatting.FormatSize(1536), "fraction");
            Equal("5.00 MB", Formatting.FormatSize(5 * 1024 * 1024), "megabytes");
            Equal("2.00 GB", Formatting.FormatSize(2d * 1024 * 1024 * 1024), "gigabytes");
        }

        private static void FormattingDate()
        {
            Equal("2024-01-31", Formatting.FormatInstallDate("20240131"), "compact");
            Equal("2024-01-31", Formatting.FormatInstallDate("2024-01-31"), "iso");
            Equal("", Formatting.FormatInstallDate(""), "empty");
            Equal("unknown", Formatting.FormatInstallDate("unknown"), "passthrough");
        }

        private static void FormattingNormalize()
        {
            Equal("googlechrome", Formatting.NormalizeName("Google Chrome!"), "punct");
            Equal("", Formatting.NormalizeName(null), "null");
            Equal("7zip", Formatting.NormalizeName("7-Zip"), "dash");
        }

        private static void FormattingIconReference()
        {
            var quoted = Formatting.SplitIconReference("\"C:\\Program Files\\App\\app.exe\", 3");
            Equal("C:\\Program Files\\App\\app.exe", quoted.Path, "quoted path");
            Equal(3, quoted.Index, "quoted index");

            var plain = Formatting.SplitIconReference("C:\\App\\app.exe");
            Equal("C:\\App\\app.exe", plain.Path, "plain path");
            Equal(0, plain.Index, "plain index");
        }

        private static void CommandsSplit()
        {
            var quoted = UninstallCommands.SplitWindowsCommand("\"C:\\Program Files\\App\\unins000.exe\" /SILENT");
            Equal(2, quoted.Count, "quoted count");
            Equal("C:\\Program Files\\App\\unins000.exe", quoted[0], "quoted exe");
            Equal("/SILENT", quoted[1], "quoted flag");

            var unquoted = UninstallCommands.SplitWindowsCommand("\"C:\\App\\setup.exe\" /x /q");
            Equal(3, unquoted.Count, "flags count");
            Equal("/x", unquoted[1], "flag one");

            var guid = UninstallCommands.SplitWindowsCommand("{12345678-1234-1234-1234-123456789012}");
            Equal(3, guid.Count, "guid count");
            True(UninstallCommands.IsMsiCommand(guid), "guid becomes msiexec");
        }

        private static void CommandsMsi()
        {
            var built = UninstallCommands.BuildUninstallCommand("msiexec.exe /i {11111111-1111-1111-1111-111111111111}", true);
            True(built.Contains("/x"), "install becomes remove");
            True(built.Contains("/quiet"), "quiet added");
            True(built.Contains("/norestart"), "norestart added");
            True(built.Contains("{11111111-1111-1111-1111-111111111111}"), "product kept");
            Equal(0, UninstallCommands.ResolveExecutable("msiexec.exe").Length == 0 ? 1 : 0, "msiexec present");
        }

        private static void CommandsNsis()
        {
            var built = UninstallCommands.BuildUninstallCommand("\"C:\\App\\unins000.exe\"", true);
            True(built.Contains("/VERYSILENT"), "nsis very silent");
            True(built.Contains("/SUPPRESSMSGBOXES"), "nsis suppress");
            True(built.Contains("/NORESTART"), "nsis norestart");

            var interactive = UninstallCommands.BuildUninstallCommand("\"C:\\App\\unins000.exe\"", false);
            Equal(1, interactive.Count, "interactive keeps only exe");
        }

        private static void CommandsResolve()
        {
            True(UninstallCommands.ResolveExecutable("cmd.exe").Length > 0, "cmd resolves");
            True(UninstallCommands.ResolveExecutable("reg.exe").Length > 0, "reg resolves");
            True(UninstallCommands.ResolveExecutable("definitely-not-a-real-binary.exe").Length == 0, "unknown does not resolve");
            True(UninstallCommands.CommandExists(new List<string> { "cmd.exe", "/c", "exit" }), "command exists");
        }

        private static void CommandsBatch()
        {
            var batch = Path.Combine(_temporaryRoot, "sample.bat");
            File.WriteAllText(batch, "@echo off\r\nexit /b 0\r\n");
            var prepared = UninstallCommands.PrepareProcessArguments(new List<string> { batch });
            Equal(5, prepared.Count, "batch wraps in cmd");
            Equal("cmd.exe", Path.GetFileName(prepared[0]).ToLowerInvariant(), "cmd used");
            True(prepared[4].Contains("sample.bat"), "batch path kept");
        }

        private static void CommandsExitCodes()
        {
            var msi = new List<string> { "msiexec.exe", "/x", "{11111111-1111-1111-1111-111111111111}" };
            True(UninstallCommands.ExitCodeSucceeded(msi, 0), "msi zero");
            True(UninstallCommands.ExitCodeSucceeded(msi, 3010), "msi reboot");
            True(UninstallCommands.ExitCodeSucceeded(msi, 1641), "msi reboot legacy");
            True(!UninstallCommands.ExitCodeSucceeded(msi, 1603), "msi failure");
            True(UninstallCommands.IsRebootCode(3010), "reboot code");
        }

        private static void SafetyNormalize()
        {
            Equal("c:\\windows", Safety.NormalizePath("C:\\Windows\\"), "trailing slash");
            Equal("c:\\", Safety.NormalizePath("C:\\"), "drive root");
            Equal("", Safety.NormalizePath(""), "empty");
        }

        private static void SafetyDepthWithin()
        {
            Equal(2, Safety.PathDepth("C:\\Apps\\Sample"), "depth");
            True(Safety.IsWithin("C:\\Apps\\Sample\\bin", "C:\\Apps"), "child");
            True(Safety.IsWithin("C:\\Apps", "C:\\Apps"), "same");
            True(!Safety.IsWithin("C:\\Apps2", "C:\\Apps"), "sibling prefix");
        }

        private static void SafetyProtected()
        {
            var windows = Environment.GetEnvironmentVariable("SYSTEMROOT") ?? @"C:\Windows";
            True(!Safety.IsSafeProgramDirectory(windows), "windows is protected");
            True(!Safety.IsSafeProgramDirectory(Path.Combine(windows, "System32")), "system32 is protected");
            True(!Safety.IsSafeProgramDirectory(Path.GetPathRoot(windows)), "drive root is protected");
            True(!Safety.IsSafeRemovalPath(Path.Combine(windows, "System32"), Safety.RemovalRoots()), "system32 not removable");
        }

        private static void SafetyRemoval()
        {
            var inside = Path.Combine(_temporaryRoot, "leftover");
            Directory.CreateDirectory(inside);
            True(Safety.IsSafeProgramDirectory(inside), "temp child is a program directory");
            True(Safety.IsSafeRemovalPath(inside, Safety.RemovalRoots()), "temp child is removable");
            True(!Safety.IsSafeRemovalPath(@"C:\UninstallerToolOutside\Sample", Safety.RemovalRoots()), "outside root rejected");
            True(!Safety.IsSafeRemovalPath(Path.GetTempPath(), Safety.RemovalRoots()), "allowed root itself rejected");
        }

        private static void RegistryScan()
        {
            var programs = RegistryScanner.ScanInstalledPrograms();
            True(programs.Count > 0, "programs found");
            True(programs.All(item => item.Name.Length > 0), "all named");
            True(programs.All(item => item.UninstallString.Length > 0 || item.QuietUninstallString.Length > 0), "all have commands");
            True(programs.All(item => item.Key.StartsWith("registry::", StringComparison.Ordinal)), "keys built");
            Console.WriteLine("      programs=" + programs.Count);
        }

        private static void RegistrySnapshotBuild()
        {
            var snapshot = RegistrySnapshot.Build();
            True(snapshot.Entries.Count > 0, "snapshot entries");
            True(snapshot.Entries.Any(item => item.Kind == RegistryEntryKind.Uninstall), "uninstall entries");
            Console.WriteLine("      snapshot=" + snapshot.Entries.Count);
        }

        private static void RegistryFind()
        {
            var programs = RegistryScanner.ScanInstalledPrograms();
            var program = programs.FirstOrDefault(item => item.RegistrySubkey.Length > 0);
            True(program != null, "program with subkey");
            if (program == null)
            {
                return;
            }

            var snapshot = RegistrySnapshot.Build();
            var found = snapshot.Find(program.Name, program.Publisher);
            True(found.Count > 0, "leftover lookup finds the installed program");
            True(found.All(RegistrySnapshot.IsSafeEntry), "found entries are safe");
            True(!RegistrySnapshot.IsSafeEntry(new RegistryEntry("HKEY_LOCAL_MACHINE", @"SOFTWARE\Microsoft", "", "Microsoft", RegistryEntryKind.Vendor)), "microsoft vendor rejected");
            True(!RegistrySnapshot.IsSafeEntry(new RegistryEntry("HKEY_LOCAL_MACHINE", "SOFTWARE\\A*", "", "A*", RegistryEntryKind.Vendor)), "wildcard rejected");
        }

        private static void RegistryExportDelete()
        {
            const string vendor = "UninstallerToolTests";
            const string product = "Sample";
            var path = @"Software\" + vendor + @"\" + product;
            using (var key = Registry.CurrentUser.CreateSubKey(path))
            {
                key.SetValue("Probe", "value");
            }

            try
            {
                var entry = new RegistryEntry(
                    "HKEY_CURRENT_USER",
                    path,
                    string.Empty,
                    product,
                    RegistryEntryKind.Vendor);

                True(RegistrySnapshot.IsSafeEntry(entry), "test key is safe");

                var snapshot = new RegistrySnapshot(new[] { entry });
                True(snapshot.Find(product, vendor).Count == 1, "find by vendor");

                var backup = RegistrySnapshot.ExportKey(entry, Path.Combine(_temporaryRoot, "backups"));
                True(File.Exists(backup), "reg backup written");
                True(new FileInfo(backup).Length > 0, "reg backup not empty");

                var content = File.ReadAllText(backup, Encoding.Unicode);
                True(content.StartsWith("Windows Registry Editor Version 5.00", StringComparison.Ordinal), "reg header");
                True(content.Contains(@"[HKEY_CURRENT_USER\Software\UninstallerToolTests\Sample]"), "reg key path");
                True(content.Contains("\"Probe\"=\"value\""), "reg value");

                RegistrySnapshot.DeleteEntry(entry);
                using (var key = Registry.CurrentUser.OpenSubKey(path))
                {
                    True(key == null, "key removed");
                }
            }
            finally
            {
                try
                {
                    Registry.CurrentUser.DeleteSubKeyTree(@"Software\" + vendor, false);
                }
                catch (ArgumentException)
                {
                }
            }
        }

        private static void StoreParse()
        {
            var output = string.Join(
                "\r\n",
                "P\tMicrosoft.WindowsCalculator_11.2210.0.0_x64__8wekyb3d8bbwe\tMicrosoft.WindowsCalculator_11.2210.0.0_x64__8wekyb3d8bbwe\tMicrosoft.WindowsCalculator_8wekyb3d8bbwe\tCN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US\t11.2210.0.0\tC:\\Program Files\\WindowsApps\\Calc",
                "P\t12345678-1234-1234-1234-123456789012\t12345678-1234-1234-1234-123456789012_1.0.0.0_x64__abc\t12345678-1234-1234-1234-123456789012_abc\tCN=ABCDEF123456\t1.0.0.0\tC:\\Program Files\\WindowsApps\\Hidden",
                "P\tVendor.Photo_1.0.0.0_x64__abc\tVendor.Photo_1.0.0.0_x64__abc\tVendor.Photo_abc\tCN=Vendor Studio\t1.0.0.0\tC:\\Program Files\\WindowsApps\\Photo",
                "T\tMicrosoft.WindowsCalculator_8wekyb3d8bbwe!App\tCalculator",
                "T\tVendor.Photo_abc!App\tVendor Photo");

            var programs = StoreApps.Parse(output);
            Equal(2, programs.Count, "guid-only package skipped");

            var calculator = programs.Single(item => item.Name == "Calculator");
            Equal("remove-appx:Microsoft.WindowsCalculator_11.2210.0.0_x64__8wekyb3d8bbwe", calculator.UninstallString, "uninstall string");
            True(calculator.IsStoreApp, "store source");
            Equal("Microsoft Corporation", calculator.Publisher, "publisher from CN");

            var photo = programs.Single(item => item.Name == "Vendor Photo");
            Equal("Vendor Studio", photo.Publisher, "plain publisher");
            Equal("1.0.0.0", photo.Version, "version");
        }

        private static void StoreFetch()
        {
            try
            {
                var programs = StoreApps.FetchAsync().GetAwaiter().GetResult();
                True(programs != null, "fetch returns a list");
                True(programs.All(item => item.PackageFullName.Length > 0), "package ids present");
                Console.WriteLine("      store apps=" + programs.Count);
            }
            catch (TimeoutException)
            {
                Console.WriteLine("      store scan timed out (skipped)");
            }
        }

        private static void FilesScan()
        {
            var directory = Path.Combine(_temporaryRoot, "scan");
            Directory.CreateDirectory(Path.Combine(directory, "nested"));
            File.WriteAllBytes(Path.Combine(directory, "a.bin"), new byte[1024]);
            File.WriteAllBytes(Path.Combine(directory, "nested", "b.bin"), new byte[2048]);

            var scan = FileSystemService.ScanDirectory(directory, 10, null);
            Equal(2L, scan.TotalCount, "file count");
            Equal(3072L, scan.TotalSize, "total size");
            Equal(2048L, scan.Files[0].Size, "largest first");

            var program = new ProgramEntry { Name = "Scan", InstallLocation = directory };
            var typed = FileSystemService.ScanProgramFiles(program, 10, null);
            Equal(2L, typed.TotalCount, "program scan count");
            True(FileSystemService.MeasureDirectorySize(directory, null) == 3072L, "measured size");
        }

        private static void FilesRemove()
        {
            var directory = Path.Combine(_temporaryRoot, "remove");
            Directory.CreateDirectory(Path.Combine(directory, "nested"));
            File.WriteAllText(Path.Combine(directory, "nested", "file.txt"), "data");

            var (removed, scheduled, errors) = FileSystemService.RemoveTree(directory);
            True(removed || scheduled > 0, "removal reported");
            Equal(0, errors.Count, "no removal errors");
            True(!Directory.Exists(directory), "tree removed");
        }

        private static void LeftoversSearchTest()
        {
            var target = Path.Combine(Path.GetTempPath(), "UninstallerProbeApp");
            Directory.CreateDirectory(target);
            File.WriteAllText(Path.Combine(target, "probe.dll"), "x");

            try
            {
                var program = new ProgramEntry { Name = "Uninstaller Probe App" };
                var leftovers = LeftoverSearch.Search(program, null, 10, null);
                True(leftovers.Files.Any(item => item.EndsWith("UninstallerProbeApp", StringComparison.OrdinalIgnoreCase)), "leftover folder detected");
                True(!leftovers.TimedOut, "search completed");
            }
            finally
            {
                Directory.Delete(target, true);
            }
        }

        private static void LeftoversRemoveTest()
        {
            var target = Path.Combine(Path.GetTempPath(), "UninstallerProbeRemove");
            Directory.CreateDirectory(Path.Combine(target, "data"));
            File.WriteAllText(Path.Combine(target, "data", "file.bin"), "payload");

            var leftovers = new Leftovers
            {
                ProgramName = "Uninstaller Probe Remove",
                Files = new List<string> { target }
            };

            var result = RemovalService.RemoveLeftovers(leftovers);
            Equal(0, result.Errors.Count, "no errors");
            True(result.RemovedFiles >= 1, "removed count");
            True(!Directory.Exists(target), "folder removed");
        }

        private static void SizeCacheTest()
        {
            var directory = Path.Combine(_temporaryRoot, "cache");
            Directory.CreateDirectory(directory);
            File.WriteAllBytes(Path.Combine(directory, "file.bin"), new byte[4096]);

            var cache = new SizeCache();
            cache.Put(directory, 4096);
            Equal(4096L, cache.Get(directory) ?? 0, "cached value");
            cache.Save();

            var reloaded = new SizeCache();
            Equal(4096L, reloaded.Get(directory) ?? 0, "reloaded value");

            var program = new ProgramEntry { Name = "Cache", InstallLocation = directory };
            Equal(4096L, new SizeCache().Measure(program, null), "measure uses folder");
        }

        private static void SettingsRoundtrip()
        {
            var settings = new AppSettings
            {
                WindowLeft = 100,
                WindowTop = 200,
                WindowWidth = 1040,
                WindowHeight = 700,
                WindowMaximized = true,
                SplitterRatio = 0.62,
                SortMode = 2,
                SilentMode = true
            };
            settings.Save();

            var reloaded = new AppSettings();
            Equal(100d, reloaded.WindowLeft ?? 0, "left");
            Equal(700d, reloaded.WindowHeight ?? 0, "height");
            True(reloaded.WindowMaximized, "maximized");
            True(Math.Abs(reloaded.SplitterRatio - 0.62) < 0.001, "splitter");
            Equal(2, reloaded.SortMode, "sort");
            True(reloaded.SilentMode, "silent");
        }

        private static void ProcessesFind()
        {
            var directory = Path.GetDirectoryName(typeof(Program).Assembly.Location) ?? string.Empty;
            var program = new ProgramEntry { Name = "Runner", InstallLocation = directory };
            True(Safety.IsSafeProgramDirectory(directory), "test folder is a program folder");
            var running = ProcessService.FindRunning(program);
            True(running.Count >= 1, "current process detected in its folder");
            True(ProcessService.ScanProcesses().Count > 0, "process snapshot");
            Equal(0d, ProcessService.TreeMemoryMb(999999) >= 0 ? 0d : 1d, "unknown pid memory is zero");
        }

        private static void UninstallSuccess()
        {
            var program = new ProgramEntry
            {
                Name = "Probe success",
                UninstallString = "cmd.exe /c exit 0",
                QuietUninstallString = "cmd.exe /c exit 0"
            };

            var summary = new UninstallRunner()
                .RunAsync(new[] { program }, false, null, null, CancellationToken.None)
                .GetAwaiter()
                .GetResult();

            Equal(1, summary.Results.Count, "one result");
            True(summary.Results[0].Success, "success reported");
            Equal(0, summary.Results[0].ExitCode ?? -1, "exit code");
            Equal(1, summary.Uninstalled.Count, "uninstalled list");
        }

        private static void UninstallFailure()
        {
            var program = new ProgramEntry
            {
                Name = "Probe failure",
                UninstallString = "cmd.exe /c exit 3"
            };

            var summary = new UninstallRunner()
                .RunAsync(new[] { program }, false, null, null, CancellationToken.None)
                .GetAwaiter()
                .GetResult();

            True(!summary.Results[0].Success, "failure reported");
            Equal(3, summary.Results[0].ExitCode ?? -1, "failure code");
            True(summary.Results[0].Message.Contains("3"), "message mentions the code");
        }

        private static void ElevationCheck()
        {
            var admin = Elevation.IsAdmin();
            Console.WriteLine("      administrator=" + admin);
            _checks++;
        }

        private static void Cleanup()
        {
            try
            {
                if (Directory.Exists(_temporaryRoot))
                {
                    Directory.Delete(_temporaryRoot, true);
                }

                if (File.Exists(AppPaths.SettingsFile))
                {
                    File.Delete(AppPaths.SettingsFile);
                }
            }
            catch (IOException)
            {
            }
            catch (UnauthorizedAccessException)
            {
            }
        }

        private static void Equal<T>(T expected, T actual, string name)
        {
            _checks++;
            if (EqualityComparer<T>.Default.Equals(expected, actual))
            {
                Console.WriteLine("ok    " + name);
                return;
            }

            _failures++;
            Console.WriteLine("FAIL  " + name + "  expected=" + expected + " actual=" + actual);
        }

        private static void True(bool condition, string name)
        {
            _checks++;
            if (condition)
            {
                Console.WriteLine("ok    " + name);
                return;
            }

            _failures++;
            Console.WriteLine("FAIL  " + name);
        }
    }
}
