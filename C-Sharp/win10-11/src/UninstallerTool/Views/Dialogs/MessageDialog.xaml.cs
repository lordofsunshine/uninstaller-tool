using System.Windows;
using System.Windows.Controls;
using UninstallerTool.Infrastructure;

namespace UninstallerTool.Views.Dialogs
{
    public enum MessageResult
    {
        Ok,
        Yes,
        No,
        Cancel
    }

    public partial class MessageDialog : Window
    {
        private MessageResult _result = MessageResult.Cancel;

        private MessageDialog()
        {
            InitializeComponent();
        }

        public static MessageResult Show(
            Window owner,
            string title,
            string message,
            params MessageResult[] buttons)
        {
            var dialog = Create(owner, title, message, buttons);
            dialog.ShowDialog();
            return dialog._result;
        }

        internal static MessageDialog Create(
            Window owner,
            string title,
            string message,
            params MessageResult[] buttons)
        {
            var dialog = new MessageDialog { Title = title ?? "Uninstaller Tool" };
            if (owner != null)
            {
                dialog.Owner = owner;
            }

            dialog.TitleLabel.Text = title ?? string.Empty;
            dialog.BodyLabel.Text = message ?? string.Empty;
            dialog.BuildButtons(buttons.Length > 0 ? buttons : new[] { MessageResult.Ok });

            dialog.Closed += (sender, args) => dialog.Owner?.Activate();
            return dialog;
        }

        public static bool Confirm(Window owner, string title, string message, bool defaultYes = true)
        {
            var result = Show(owner, title, message, MessageResult.Yes, MessageResult.No);
            return result == MessageResult.Yes;
        }

        public static bool Notify(Window owner, string title, string message)
        {
            Show(owner, title, message, MessageResult.Ok);
            return true;
        }

        private void BuildButtons(MessageResult[] buttons)
        {
            ButtonRow.Children.Clear();
            var primary = buttons.Length > 0 ? buttons[buttons.Length - 1] : MessageResult.Ok;

            foreach (var button in buttons)
            {
                var control = new Button
                {
                    Content = Label(button),
                    MinWidth = 86,
                    Margin = new Thickness(8, 0, 0, 0),
                    Style = (Style)FindResource(button == primary ? "PrimaryButton" : "SecondaryButton"),
                    Padding = new Thickness(18, 8, 18, 8)
                };

                var value = button;
                control.Click += (sender, args) =>
                {
                    _result = value;
                    DialogResult = value != MessageResult.Cancel;
                    Close();
                };

                ButtonRow.Children.Add(control);
            }
        }

        private static string Label(MessageResult result)
        {
            switch (result)
            {
                case MessageResult.Yes:
                    return "Yes";
                case MessageResult.No:
                    return "No";
                case MessageResult.Cancel:
                    return "Cancel";
                default:
                    return "OK";
            }
        }
    }
}
