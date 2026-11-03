using System;
using System.Diagnostics;
using System.Text;
using System.Threading.Tasks;
using UninstallerTool.Core;

namespace UninstallerTool.Infrastructure
{
    internal sealed class PowerShellResult
    {
        public PowerShellResult(int exitCode, string output, string error)
        {
            ExitCode = exitCode;
            Output = output ?? string.Empty;
            Error = error ?? string.Empty;
        }

        public int ExitCode { get; }

        public string Output { get; }

        public string Error { get; }
    }

    internal static class PowerShellRunner
    {
        public static async Task<PowerShellResult> RunAsync(string script, TimeSpan timeout)
        {
            var command = (script ?? string.Empty).Replace("\"", "\\\"");
            var startInfo = new ProcessStartInfo
            {
                FileName = UninstallCommands.PowerShellPath(),
                Arguments = "-NoLogo -NoProfile -NonInteractive -Command \"" + command + "\"",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8
            };

            using (var process = new Process { StartInfo = startInfo })
            {
                if (!process.Start())
                {
                    throw new InvalidOperationException("Could not start PowerShell");
                }

                var outputTask = process.StandardOutput.ReadToEndAsync();
                var errorTask = process.StandardError.ReadToEndAsync();

                var completed = await WaitAsync(process, timeout).ConfigureAwait(false);
                if (!completed)
                {
                    try
                    {
                        process.Kill();
                    }
                    catch (InvalidOperationException)
                    {
                    }

                    throw new TimeoutException("PowerShell did not finish in time");
                }

                var output = await outputTask.ConfigureAwait(false);
                var error = await errorTask.ConfigureAwait(false);
                return new PowerShellResult(process.ExitCode, output, error);
            }
        }

        private static async Task<bool> WaitAsync(Process process, TimeSpan timeout)
        {
            var deadline = DateTime.UtcNow + timeout;
            while (DateTime.UtcNow < deadline)
            {
                if (process.HasExited)
                {
                    return true;
                }

                await TaskEx.Delay(50).ConfigureAwait(false);
            }

            return process.HasExited;
        }
    }
}
