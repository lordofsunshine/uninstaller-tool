using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;
using UninstallerTool.Theme;

namespace UninstallerTool.Views.Dialogs
{
    public partial class InfoDialog : Window
    {
        public InfoDialog(ProgramEntry program)
        {
            InitializeComponent();
            TitleLabel.Text = program.Name;

            var icon = IconLoader.Load(program.Icon, 32);
            if (icon == null)
            {
                ProgramIcon.Visibility = Visibility.Collapsed;
            }
            else
            {
                ProgramIcon.Source = icon;
            }

            AddRow("Publisher:", program.Publisher);
            AddRow("Install Date:", Formatting.FormatInstallDate(program.InstallDate));
            AddRow("Version:", program.Version);
            AddRow("Location:", program.InstallLocation);
            AddRow("Uninstall Command:", program.UninstallString);

            if (program.SizeBytes > 0)
            {
                AddRow("Size:", Formatting.FormatSize(program.SizeBytes));
            }

            if (program.IsStoreApp)
            {
                AddRow("Store package:", program.PackageFullName);
            }
        }

        private void AddRow(string caption, string value)
        {
            var row = new Grid { Margin = new Thickness(0, 0, 0, 8) };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(140) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            var label = new TextBlock
            {
                Text = caption,
                FontWeight = FontWeights.SemiBold,
                Foreground = (Brush)FindResource(ThemeManager.TextSecondaryBrushKey),
                TextWrapping = TextWrapping.Wrap
            };

            var content = new TextBlock
            {
                Text = string.IsNullOrWhiteSpace(value) ? "Not available" : value,
                Foreground = (Brush)FindResource(ThemeManager.TextBrushKey),
                TextWrapping = TextWrapping.Wrap
            };

            Grid.SetColumn(label, 0);
            Grid.SetColumn(content, 1);
            row.Children.Add(label);
            row.Children.Add(content);
            Rows.Children.Add(row);
        }

        private void OnDoneClick(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
