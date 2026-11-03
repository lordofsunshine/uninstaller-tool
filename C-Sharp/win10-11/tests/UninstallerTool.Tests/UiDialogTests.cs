using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using UninstallerTool.Models;
using UninstallerTool.Theme;
using UninstallerTool.Views.Dialogs;

namespace UninstallerTool.Tests
{
    internal static class UiDialogTests
    {
        public static void Run(Action<bool, string> check)
        {
            var thread = new Thread(() => RunOnSta(check));
            thread.SetApartmentState(ApartmentState.STA);
            thread.Start();
            thread.Join();
        }

        private static void RunOnSta(Action<bool, string> check)
        {
            var application = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
            application.Resources.MergedDictionaries.Add(new ResourceDictionary
            {
                Source = new Uri("pack://application:,,,/UninstallerTool;component/Theme/Theme.xaml")
            });
            ThemeManager.Apply(Palette.Light);

            var directory = Path.Combine(
                Path.GetTempPath(),
                "UninstallerToolDialog_" + Guid.NewGuid().ToString("N").Substring(0, 6));
            Directory.CreateDirectory(directory);
            File.WriteAllBytes(Path.Combine(directory, "file.bin"), new byte[2048]);

            try
            {
                var program = new ProgramEntry
                {
                    Name = "Dialog Probe",
                    Publisher = "Probe Vendor",
                    Version = "1.2.3",
                    InstallDate = "20240102",
                    InstallLocation = directory,
                    UninstallString = "cmd.exe /c exit 0",
                    SizeKb = 2048
                };

                var info = new InfoDialog(program);
                info.Show();
                info.UpdateLayout();
                check(info.Title == "Program Information", "dialog.info.title");
                check(
                    ContainsText(info, "Publisher:") &&
                    ContainsText(info, "Probe Vendor") &&
                    ContainsText(info, "2024-01-02") &&
                    ContainsText(info, "2.00 MB"),
                    "dialog.info.fields");
                info.Close();

                var disk = new DiskSpaceDialog(new List<ProgramEntry> { program });
                disk.Show();
                disk.UpdateLayout();
                check(disk.Title == "Disk Space Usage", "dialog.disk.title");
                check(
                    ContainsText(disk, "Top 10 largest programs") &&
                    ContainsText(disk, "Usage by publisher") &&
                    ContainsText(disk, "Total size"),
                    "dialog.disk.sections");
                disk.Close();

                var leftovers = new Leftovers
                {
                    ProgramName = "Dialog Probe",
                    Files = new List<string> { directory },
                    Registry = new List<RegistryEntry>
                    {
                        new RegistryEntry("HKEY_CURRENT_USER", @"Software\Probe\Sample", string.Empty, "Sample", RegistryEntryKind.Vendor)
                    }
                };

                var leftoversDialog = new LeftoversDialog(leftovers);
                leftoversDialog.Show();
                leftoversDialog.UpdateLayout();
                check(leftoversDialog.Title == "Leftover Files and Entries", "dialog.leftovers.title");
                check(
                    ContainsText(leftoversDialog, "Files (1 item)") &&
                    ContainsText(leftoversDialog, "Registry entries (1 item)"),
                    "dialog.leftovers.sections");
                leftoversDialog.Close();

                var preview = new FilePreviewDialog(program);
                preview.Show();
                preview.UpdateLayout();
                check(preview.Title == "Folder preview \u2014 Dialog Probe", "dialog.preview.title");
                preview.Close();

                var message = MessageDialog.Create(null, "Probe title", "Probe body", MessageResult.Yes, MessageResult.No);
                message.Show();
                message.UpdateLayout();
                check(
                    ContainsText(message, "Probe title") &&
                    ContainsText(message, "Probe body") &&
                    ContainsText(message, "Yes") &&
                    ContainsText(message, "No"),
                    "dialog.message.content");
                message.Close();
            }
            finally
            {
                try
                {
                    Directory.Delete(directory, true);
                }
                catch (IOException)
                {
                }
                catch (UnauthorizedAccessException)
                {
                }

                application.Shutdown();
            }
        }

        private static bool ContainsText(DependencyObject root, string value)
        {
            return CollectText(root).Any(item => item == value || item.Contains(value));
        }

        private static IEnumerable<string> CollectText(DependencyObject root)
        {
            if (root == null)
            {
                yield break;
            }

            if (root is TextBlock textBlock)
            {
                yield return textBlock.Text ?? string.Empty;
            }
            else if (root is ContentControl content && content.Content is string label)
            {
                yield return label;
            }
            else if (root is TextBox box)
            {
                yield return box.Text ?? string.Empty;
            }

            var count = VisualTreeHelper.GetChildrenCount(root);
            for (var index = 0; index < count; index++)
            {
                foreach (var text in CollectText(VisualTreeHelper.GetChild(root, index)))
                {
                    yield return text;
                }
            }
        }
    }
}
