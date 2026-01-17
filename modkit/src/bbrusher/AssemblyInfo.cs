/*
bbrusher is a program to pack and unpack Battle Brothers .brush files.

Written in 2019 by Adam Milazzo
http://www.adammil.net/

This program is released into the public domain.
*/
using System;
using System.Reflection;
using System.Runtime.InteropServices;

[assembly: AssemblyTitle("bbrusher")]
[assembly: AssemblyDescription("A program to pack and unpack Battle Brothers .brush files.")]
#if DEBUG
[assembly: AssemblyConfiguration("Debug")]
#else
[assembly: AssemblyConfiguration("Release")]
#endif
[assembly: AssemblyProduct("Battle Brothers mod kit")]
[assembly: AssemblyCopyright("Adam Milazzo 2019")]

[assembly: CLSCompliant(true)]
[assembly: ComVisible(false)]

[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]
