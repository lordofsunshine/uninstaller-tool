using System;
using System.Windows;
using System.Windows.Threading;
using UninstallerTool.Infrastructure;
using UninstallerTool.Theme;
using UninstallerTool.Views;
using UninstallerTool.Views.Dialogs;

namespace UninstallerTool
{
    public partial class App : Application
    {
        protected override void OnStartup(StartupEventArgs e)
        {
            Log.Initialize();
            ThemeManager.Initialize();
            EventManager.RegisterClassHandler(typeof(Window), FrameworkElement.LoadedEvent, new RoutedEventHandler(OnWindowLoaded));
            DispatcherUnhandledException += OnDispatcherUnhandledException;
            AppDomain.CurrentDomain.UnhandledException += OnDomainUnhandledException;

            base.OnStartup(e);

            var window = new MainWindow();
            MainWindow = window;
            window.Show();
        }

        private static void OnWindowLoaded(object sender, RoutedEventArgs e)
        {
            if (sender is Window window)
            {
                ThemeManager.AttachWindow(window);
                WindowSizing.Fit(window);
            }
        }

        private void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
        {
            Log.Exception("Unhandled exception", e.Exception);
            MessageDialog.Show(
                MainWindow,
                "Unexpected error",
                "The application hit an unexpected error." + Environment.NewLine +
                "Details were written to the log file:" + Environment.NewLine +
                AppPaths.LogFile,
                MessageResult.Ok);
            e.Handled = true;
        }

        private void OnDomainUnhandledException(object sender, UnhandledExceptionEventArgs e)
        {
            Log.Exception("Fatal exception", e.ExceptionObject as Exception);
        }
    }
}
