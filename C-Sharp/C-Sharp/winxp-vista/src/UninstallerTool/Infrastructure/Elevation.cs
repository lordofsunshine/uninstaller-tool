using System;
using System.Security.Principal;

namespace UninstallerTool.Infrastructure
{
    internal static class Elevation
    {
        public static bool IsAdmin()
        {
            try
            {
                using (var identity = WindowsIdentity.GetCurrent())
                {
                    return new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator);
                }
            }
            catch (Exception)
            {
                return false;
            }
        }
    }
}
