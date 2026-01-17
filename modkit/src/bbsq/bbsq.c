#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <Windows.h>

#include <squirrel.h>
#include <sqstdblob.h>
#include <sqstdsystem.h>
#include <sqstdio.h>
#include <sqstdmath.h>
#include <sqstdstring.h>
#include <sqstdaux.h>

#include "xxtea.h"

#define scfprintf fprintf
#define scvprintf vfprintf

void printfunc(HSQUIRRELVM v, const SQChar *s, ...)
{
    va_list vl;
    va_start(vl, s);
    scvprintf(stdout, s, vl);
    va_end(vl);
}

void errorfunc(HSQUIRRELVM v, const SQChar *s, ...)
{
    va_list vl;
    va_start(vl, s);
    scvprintf(stderr, s, vl);
    va_end(vl);
}

void PrintUsage()
{
    scfprintf(stderr, _SC("Usage: bbsq -d|-e <files>.\n")
              _SC(" -d <files>   Decrypts <files> (which must be encrypted .cnut files) and\n")
              _SC("              writes them as unencrypted .cnut files.\n")
              _SC(" -e <files>   Reads <files> (which should be .nut or unencrypted .cnut files),\n")
              _SC("              compiles them if necessary, and creates encrypted .cnut files.\n")
              _SC("Examples: bbsq d foo.cnut\n")
              _SC("          bbsq e foo.cnut\n")
              _SC("          bbsq e foo.nut bar.nut baz.nut\n"));
}

typedef struct
{
    SQFILE in, out;
    const char *inPath, *outPath;
    char command;
} Operation;

SQInteger read_and_cipher(SQUserPointer ufile, SQUserPointer buffer, SQInteger length)
{
    const Operation *op = (const Operation*)ufile;
    length = sqstd_fread(buffer, 1, length, op->in);
    if (length >= 8) // if we need to cipher the data read...
    {
        static int key[4] = { 238473842, 20047425, 14005, 978629342 };
        if (op->command == 'E') encrypt((uint32_t*)buffer, length / 4, key);
        else decrypt((uint32_t*)buffer, length / 4, key);

        // now write the result to the output
        if (op->out) // if we have a separate output file...
        {
            SQInteger start = sqstd_ftell(op->in) - length; // overwrite the block within it
            sqstd_fseek(op->out, start, SQ_SEEK_SET);
            sqstd_fwrite(buffer, 1, length, op->out);
        }
        else // otherwise, we're updating the input file...
        {
            sqstd_fseek(op->in, -length, SQ_SEEK_CUR); // seek back to the start of the data
            sqstd_fwrite(buffer, 1, length, op->in); // and overwrite it
            sqstd_fflush(op->in); // a flush is required before transitioning from write back to read
        }

        // if we encrypted the data, decrypt it again so we don't return garbage to Squirrel
        if (op->command == 'E') decrypt((uint32_t*)buffer, length / 4, key);
    }

    return length;
}

SQRESULT cipher_file(HSQUIRRELVM vm, Operation *op)
{
    op->out = NULL;
    op->in = sqstd_fopen(op->inPath, op->outPath ? _SC("rb") : _SC("r+b"));
    if (!op->in) return SQ_ERROR;

    SQRESULT result;
    unsigned short us;
    SQInteger read = sqstd_fread(&us, 2, 1, op->in);
    if (read && us == SQ_BYTECODE_STREAM_TAG) // if the source file is a compiled script...
    {
        if (op->outPath) // open the output file if we have one
        {
            op->out = sqstd_fopen(op->outPath, _SC("r+b"));
            if (!op->out) return SQ_ERROR;
        }

        sqstd_fseek(op->in, 0, SQ_SEEK_SET);
        result = sq_readclosure(vm, read_and_cipher, op);
    }
    else if (op->command != 'E' || !op->outPath)
    {
        result = SQ_ERROR; // fail if it's not supposed to be a text script...
    }
    else // otherwise, the source is a text script and we're encrypting it
    {
        sqstd_fclose(op->in); // close the input and let sqstd_loadfile do the heavy lifting
        op->in = NULL;
        result = sqstd_loadfile(vm, op->inPath, SQTrue);
        if (SQ_SUCCEEDED(result)) result = sqstd_writeclosuretofile(vm, op->outPath); // write the unencrypted output
        if (SQ_SUCCEEDED(result)) // now encrypt the output
        {
            op->in = sqstd_fopen(op->outPath, _SC("r+b"));
            if (!op->in) return SQ_ERROR;
            result = sq_readclosure(vm, read_and_cipher, op);
        }
    }

    if (op->in) { sqstd_fclose(op->in); op->in = NULL; }
    if (op->out) { sqstd_fclose(op->out); op->out = NULL; }

    return result;
}

SQRESULT decrypt_file(HSQUIRRELVM vm, const char *infile)
{
    Operation op;
    op.inPath = infile;
    op.outPath = NULL;
    op.command = 'D';
    return cipher_file(vm, &op);
}

SQRESULT encrypt_file(HSQUIRRELVM vm, const char *infile)
{
    char outfile[_MAX_PATH + 4];
    strcpy_s(outfile, sizeof(outfile), infile);
    char *ext = strrchr(outfile, '.'); // change the extension to .cnut
    BOOL nameChanged = FALSE;
    if (ext && _strcmpi(ext, ".cnut"))
    {
        if (!ext) strcat_s(outfile, sizeof(outfile), ".cnut");
        else strcpy_s(ext, sizeof(outfile) - (ext - outfile), ".cnut");
        if (!CopyFile(infile, outfile, FALSE)) return SQ_ERROR;
        nameChanged = TRUE;
    }

    Operation op;
    op.inPath = infile;
    op.outPath = nameChanged ? outfile : NULL;
    op.command = 'E';
    return cipher_file(vm, &op);
}

int main(int argc, char* argv[])
{
    if (argc < 3 || (_strcmpi(argv[1], "-d") && _strcmpi(argv[1], "-e")))
    {
        PrintUsage();
        return 1;
    }

    char command = toupper(argv[1][1]);
    for (int i = 2; i < argc; i++) // for each source file...
    {
        HSQUIRRELVM v = sq_open(1024);
        sq_setprintfunc(v, printfunc, errorfunc);
        sq_pushroottable(v);
        sqstd_register_bloblib(v);
        sqstd_register_iolib(v);
        sqstd_register_systemlib(v);
        sqstd_register_mathlib(v);
        sqstd_register_stringlib(v);
        sqstd_seterrorhandlers(v);

        SQRESULT result = command == 'D' ? decrypt_file(v, argv[i]) : encrypt_file(v, argv[i]);
        if (!SQ_SUCCEEDED(result))
        {
            const char *err;
            sq_getlasterror(v);
            if (!SQ_SUCCEEDED(sq_getstring(v, -1, &err)))
                err = _SC("<unknown>");
            scprintf(_SC("File %s had error %s\n"), argv[i], err);
        }

        sq_close(v);
        if (!SQ_SUCCEEDED(result)) return 2;
    }

    return 0;
}

