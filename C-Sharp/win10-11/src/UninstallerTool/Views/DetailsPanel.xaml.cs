using System;
using System.Windows;
using System.Windows.Controls;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Views
{
    public partial class DetailsPanel : UserControl
    {
        public DetailsPanel()
        {
            InitializeComponent();
            PreviewButton.Click += (sender, args) => PreviewRequested?.Invoke(this, EventArgs.Empty);
            InfoButton.Click += (sender, args) => InfoRequested?.Invoke(this, EventArgs.Empty);
        }

        public event EventHandler PreviewRequested;

        public event EventHandler InfoRequested;

        public ProgramEntry Program { get; private set; }

        public Button Preview => PreviewButton;

        public Button Info => InfoButton;

        public void SetProgram(ProgramEntry program)
        {
            Program = program;
            if (program == null)
            {
                Placeholder.Visibility = Visibility.Visible;
                ContentRoot.Visibility = Visibility.Collapsed;
                return;
            }

            Placeholder.Visibility = Visibility.Collapsed;
            ContentRoot.Visibility = Visibility.Visible;

            ProgramName.Text = program.Name;
            PublisherValue.Text = Fallback(program.Publisher);
            VersionValue.Text = Fallback(program.Version);
            InstalledValue.Text = Fallback(Formatting.FormatInstallDate(program.InstallDate));
            SizeValue.Text = program.SizeBytes > 0 ? Formatting.FormatSize(program.SizeBytes) : "\u2014";
            LocationValue.Text = Fallback(program.InstallLocation);
        }

        private static string Fallback(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? "\u2014" : value;
        }
    }
}
