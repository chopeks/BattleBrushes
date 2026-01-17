This package contains a mod kit for the game Battle Brothers. The mod kit was
assembled and partially written by Adam Milazzo (http://www.adammil.net) and
also contains programs by others as described below.

Version: 9
Web page: http://www.adammil.net/blog/v133_Battle_Brothers_mod_kit.html
Contact: adam@adammil.net  or  http://www.adammil.net/contact.html

CONTENTS
--------
bin/
* bbrusher.exe
    A program that can unpack and repack the game's sprite sheets (i.e. the
    .brush files and gfx images). The program was written by Adam Milazzo.
    Run the program without arguments for a usage summary.

* bbsq.exe
    A program capable of decrypting and encrypting Battle Brothers
    compiled script (.cnut) files. The program was written by Adam Milazzo.
    Example usage to decrypt three scripts.
      bbsq -d foo.cnut bar.cnut baz.cnut
    The -e option can be used to reencrypt, and the program can be run without
    arguments for a usage summary.

* masscompile.bat
    A batch script to recursively compile and encrypt a large number of
    .cnut files at once. The script must be run from the directory containing
    bbsq and sq. The directory to process is passed as the first parameter.
    The expected usage is to take some mod you're working on in the
    bbros\data\scripts directory, and compile and encrypt it to prepare it for
    publishing. Example:
      massdecompile c:\bbros\data\scripts

* massdecompile.bat
    A batch script to recursively decrypt and decompile a large number of
    .cnut files at once. The script must be run from the directory containing
    bbsq.exe and sq.exe. The directory to process is passed as the first
    parameter. The expected usage is to take the bbros\data\data_001.dat file
    (which is really a .zip file), unpack it somewhere (NOT into your game's
    data directory!) and then decrypt all the scripts en masse. Example:
      massdecompile c:\path\to\scripts

* nutcracker.exe
    A Squirrel decompiler written by "DamianXVI". The program has some bugs,
    but it's the best decompiler available at the moment. The project page is
    https://github.com/darknesswind/NutCracker. Example usage to decompile a
    script and print it to the screen:
      nutcracker knife.cnut
    The output can of course be redirected to a file:
      nutcracker knife.cnut >knife.nut

* sq.exe
    The standard Squirrel compiler, written by Alberto Demichelis, and which
    can be used to recompile a script that you've edited. This is not strictly
    necessary, since Battle Brothers will read uncompiled (plain-text) scripts
    as well if they have the .nut extension, but this can be done to
    potentially speed up the loading of the game for a large mod by
    precompiling the scripts. Example usage:
      sq -o foo.cnut -c foo.nut
    Before using the compiled file in the game, don't forget to encrypt it:
      bbsq -e foo.cnut

src/
  Contains source code for the above programs, or links to it.


USAGE
-----
The basic usage of the individual programs is described above, but the
expected workflow is:
1. Unpack the scripts from your Battle Brothers game.
  a. Browse to your Battle Brothers installation directory.
  b. Rename data/data_001.dat to data_001.zip
  c. Open data/data_001.zip and extract the scripts directory. Don't extract
     it into your game's data directory! If you mass decompile the files
     there, it has the potential to mess up the game. Extract the scripts to
     your desktop or something.
  d. Rename data_001.zip back to data_001.dat
2. Decompile all of the scripts.
  a. Using the command prompt, navigate to the mod kit's bin directory, which
     contains massdecompile.bat and the other programs.
  b. Run the following command, using the path to the scripts extracted above:
     massdecompile.bat c:\path\to\scripts
3. Edit scripts to your liking.
4. Package scripts into mods. See the mod kit web page for more details.
   http://www.adammil.net/blog/v133_Battle_Brothers_mod_kit.html


VERSION HISTORY
---------------
Version 1:
  Initial release

Version 2:
  Attempted to fix a critical bug in the NutCracker decompiler:
    https://github.com/darknesswind/NutCracker/issues/20
  I don't know whether my fix is correct. Hopefully it is. If the author
  makes an official fix, I'll incorporate that in the next version.

Version 3:
  Attempted to fix another serious bug in the NutCracker decompiler:
    https://github.com/darknesswind/NutCracker/issues/21

Version 4:
  Attempted to fix another critical bug in the NutCracker decompiler:
    https://github.com/darknesswind/NutCracker/issues/22

Version 5:
  Added a program to pack and unpack the game's sprite sheets

Version 6:
  Fixed more bugs (one of which was critical) in the NutCracker decompiler:
    https://github.com/darknesswind/NutCracker/issues/23
    https://github.com/darknesswind/NutCracker/issues/24

Version 7:
  Deciphered and implemented the "group ID" hash to allow more types of
  sprites to added with bbrusher. (Should be all of them now.) Also made
  nutcracker floating point output prettier.

Version 8:
  Hopefully fixed another four serious bugs in NutCracker:
    https://github.com/darknesswind/NutCracker/issues/25
    https://github.com/darknesswind/NutCracker/issues/26
    https://github.com/darknesswind/NutCracker/issues/28
    https://github.com/darknesswind/NutCracker/issues/29
  Also found a fifth bug but didn't fix it because it might not affect
  Battle Brothers scripts:
    https://github.com/darknesswind/NutCracker/issues/27

Version 9:
  Improved NutCracker's handling of non-ANSI strings by switching to UTF-8
