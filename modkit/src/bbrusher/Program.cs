/*
bbrusher is a program to pack and unpack Battle Brothers .brush files.

Written in 2019 by Adam Milazzo
http://www.adammil.net/

This program is released into the public domain.
*/
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Xml;
using AdamMil.Utilities;
using RectanglePacker = AdamMil.Mathematics.Geometry.RectanglePacker;

namespace bbrusher
{
  sealed class Program
  {
    static int Main(string[] args)
    {
      string brushPath = null, inOutDir = null, gfxDir = null;
      char command = '\0';
      bool badUsage = false;
      for(int i=0; i<args.Length && !badUsage; i++)
      {
        if(string.Equals(args[i], "--gfxPath", StringComparison.OrdinalIgnoreCase))
        {
          if(gfxDir == null && ++i < args.Length) gfxDir = args[i];
          else badUsage = true;
        }
        else if(command == '\0')
        {
          if(string.Equals(args[i], "pack", StringComparison.OrdinalIgnoreCase)) command = 'P';
          else if(string.Equals(args[i], "unpack", StringComparison.OrdinalIgnoreCase)) command = 'U';
          else badUsage = true;
        }
        else if(brushPath == null)
        {
          brushPath = args[i];
        }
        else if(inOutDir == null)
        {
          inOutDir = args[i];
        }
        else
        {
          badUsage = true;
        }
      }

      if(badUsage || command == '\0' || brushPath == null)
      {
        PrintUsage();
        return 1;
      }

      if(inOutDir == null) inOutDir = Path.GetFileNameWithoutExtension(brushPath);
      if(gfxDir == null) gfxDir = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(brushPath)), "..");

      try
      {
        if(command == 'U') Unpack(brushPath, inOutDir, gfxDir);
        else Pack(brushPath, inOutDir, gfxDir);
        return 0;
      }
      catch (Exception ex)
      {
        Console.WriteLine("ERROR: " + ex.GetType().Name + " - " + ex.Message);
        return 2;
      }
    }

    static void Pack(string brushPath, string inDir, string gfxDir)
    {
      var xml = new XmlDocument();
      xml.Load(Path.Combine(inDir, "metadata.xml"));
      XmlElement brush = xml.DocumentElement;

      Console.WriteLine("Loading images...");
      var frames = new Dictionary<string, Bitmap>();
      foreach(XmlElement sprite in brush.ChildNodes.OfType<XmlElement>())
      {
        IEnumerable<XmlElement> frameList = sprite.ChildNodes.OfType<XmlElement>();
        if(!frameList.Any()) frameList = new[] { sprite };
        foreach(XmlElement frame in frameList)
        {
          string name = frame.GetAttribute("img");
          Console.WriteLine(name);
          frames[name] = new Bitmap(Path.Combine(inDir, name));
        }
      }

      Console.WriteLine("Packing rectangles...");
      int spacing = frames.Count > 1 ? 1 : 0;
      int minArea = frames.Values.Sum(f => (f.Width+spacing) * (f.Height+spacing));
      int imgWidth = Utility.RoundUpToPowerOfTwo((int)Math.Round(Math.Sqrt(minArea)));
      int imgHeight = Utility.RoundUpToPowerOfTwo(minArea / imgWidth);
      var framePoints = new Dictionary<string, Point>(frames.Count);
      Size[] sizes = frames.Values.Select(f => f.Size).ToArray();
      while(true)
      {
        Point?[] points;
        var packer = new RectanglePacker(imgWidth, imgHeight, spacing);
        if(packer.TryAdd(sizes, out points))
        {
          int fi = 0;
          foreach(string name in frames.Keys) framePoints[name] = points[fi++].Value;
          break;
        }

        if(imgWidth > imgHeight) imgHeight *= 2;
        else imgWidth *= 2;
      }

      string imgName = brush.GetAttribute("name");
      Console.WriteLine("Writing " + imgName + " ({0}x{1})...", imgWidth, imgHeight);
      using(var img = new Bitmap(imgWidth, imgHeight, PixelFormat.Format32bppArgb))
      using(var bw = new BinaryWriter(File.OpenWrite(brushPath)))
      {
        BitmapData imgBits = img.LockBits(new Rectangle(0, 0, imgWidth, imgHeight), ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
        bw.Write(0xBAADFAAD);
        bw.Write(brush.GetUInt16Attribute("version", 17));
        WriteString(bw, imgName);

        bw.Write((ushort)imgWidth);
        bw.Write((ushort)imgHeight);
        for(int i = 0; i < 12; i++)
        {
          byte defaultValue = (byte)(i == 0 || i == 2 || i == 3 || i == 4 || i == 8 ? 1 : 0);
          bw.Write(brush.GetByteAttribute("b" + (i+1).ToStringInvariant(), defaultValue));
        }

        bw.Write(brush.ChildNodes.OfType<XmlElement>().Count());
        for(int i = 0; i < 2; i++) bw.Write(brush.GetByteAttribute("b" + (i+13).ToStringInvariant()));
        bw.Write(brush.GetInt32Attribute("i0", 1000));
        foreach(XmlElement sprite in brush.ChildNodes.OfType<XmlElement>())
        {
          string name = sprite.GetAttribute("id");
          bw.Write(GetHex64Attribute(sprite, "hash", HashName(name)));
          WriteString(bw, name);
          bw.Write(GetHex64Attribute(sprite, "L0", 0xBF795EF4D3FE85C5));

          string firstFrameName = (sprite.GetFirstChildElement() ?? sprite).GetAttribute("img");
          Bitmap firstFrame = frames[firstFrameName];
          int spriteWidth = sprite.GetInt32Attribute("width", firstFrame.Width);
          int spriteHeight = sprite.GetInt32Attribute("height", firstFrame.Height);
          bw.Write(spriteWidth);
          bw.Write(spriteHeight);
          bw.Write(sprite.GetInt16Attribute("offsetX"));
          bw.Write(sprite.GetInt16Attribute("offsetY"));
          bw.Write(GetHex32Attribute(sprite, "f", 0x6400));
          for(int i = 0; i < 5; i++) bw.Write(sprite.GetByteAttribute("b" + (i+1).ToStringInvariant()));
          bw.Write(sprite.GetSingleAttribute("rotSpeed"));
          for(int i = 0; i < 4; i++)
          {
            byte defaultValue = (byte)(i == 0 ? 3 : i == 1 ? 4 : 0);
            bw.Write(sprite.GetByteAttribute("b" + (i+6).ToStringInvariant(), defaultValue));
          }

          bw.Write(sprite.GetSingleAttribute("f1"));
          bw.Write(sprite.GetSingleAttribute("f2"));
          bw.Write(GetHex32Attribute(sprite, "ic", 0));
          bw.Write(sprite.GetSingleAttribute("f3", 2));

          IEnumerable<XmlElement> frameList = sprite.ChildNodes.OfType<XmlElement>();
          if(!frameList.Any()) frameList = new[] { sprite };
          bw.Write((ushort)frameList.Count());
          foreach(XmlElement frame in frameList)
          {
            string frameName = frame.GetAttribute("img");
            WriteString(bw, frameName);
            Bitmap f = frames[frameName];
            Point point = framePoints[frameName];
            bw.Write((float)point.X / imgWidth);
            bw.Write((float)(point.X + f.Width) / imgWidth);
            bw.Write((float)point.Y / imgHeight);
            bw.Write((float)(point.Y + f.Height) / imgHeight);

            int leftEdge = -(f.Width+1)/2, rightEdge = f.Width/2, topEdge = -(f.Height+1)/2, bottomEdge = f.Height/2;
            bw.Write(frame.GetSingleAttribute("left", leftEdge));
            bw.Write(frame.GetSingleAttribute("right", rightEdge));
            bw.Write(frame.GetSingleAttribute("top", topEdge));
            bw.Write(frame.GetSingleAttribute("bottom", bottomEdge));

            Rectangle srcRect = new Rectangle(0, 0, f.Width, f.Height);
            BitmapData fbits = f.LockBits(srcRect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
            FlipBlit(fbits, srcRect, imgBits, point.X, point.Y);
            f.UnlockBits(fbits);
          }

          for(int i = 0; i < 3; i++) bw.Write(sprite.GetByteAttribute("b" + (i+10).ToStringInvariant()));
        }

        img.UnlockBits(imgBits);
        string imgPath = Path.Combine(gfxDir, imgName);
        Directory.CreateDirectory(Path.GetDirectoryName(imgPath));
        img.Save(imgPath, ImageFormat.Png);
      }
    }

    static void Unpack(string brushPath, string outDir, string gfxDir)
    {
      using(var br = new BinaryReader(File.OpenRead(brushPath)))
      {
        if(br.ReadUInt32() != 0xBAADFAAD) throw new InvalidDataException("Not a Battle Brothers .brush file.");
        int version = br.ReadUInt16();
        if(version != 17) throw new NotSupportedException("Unsupported .brush version: " + version);
        string imgName = ReadString(br);
        Console.WriteLine("Opening " + imgName + "...");
        using(var img = new Bitmap(Path.Combine(gfxDir, imgName)))
        {
          var imgBits = img.LockBits(new Rectangle(0, 0, img.Width, img.Height), ImageLockMode.ReadOnly, img.PixelFormat);
          var xml = new XmlDocument();
          XmlElement brush = xml.CreateElement("brush");
          xml.AppendChild(brush);
          brush.SetAttribute("name", imgName);
          brush.SetAttribute("version", version);

          int imgWidth = br.ReadUInt16(), imgHeight = br.ReadUInt16();
          if(imgWidth != img.Width || imgHeight != img.Height) Console.WriteLine("WARN: Image dimensions don't match .brush");
          byte[] ibh = br.ReadBytes(12); // unknown values. mostly booleans?
          for(int i = 0; i < ibh.Length; i++)
          {
            int defaultValue = i == 0 || i == 2 || i == 3 || i == 4 || i == 8 ? 1 : 0;
            if(ibh[i] != defaultValue) brush.SetAttribute("b" + (i+1).ToStringInvariant(), ibh[i]);
          }

          int spriteCount = br.ReadInt32();
          ibh = br.ReadBytes(2); // unknown values. booleans?
          for(int i = 0; i < ibh.Length; i++)
          {
            if(ibh[i] != 0) brush.SetAttribute("b" + (i+13).ToStringInvariant(), ibh[i]);
          }

          uint iih = br.ReadUInt32(); // unknown. usually 1000 but sometimes 4 or 5
          if(iih != 1000) brush.SetAttribute("i0", iih);

          for(int si = 0; si < spriteCount; si++)
          {
            var sprite = xml.CreateElement("sprite");
            ulong hash = br.ReadUInt64();
            string spriteName = ReadString(br);
            sprite.SetAttribute("id", spriteName);
            if(hash != HashName(spriteName)) sprite.SetAttribute("hash", hash.ToString("X16"));

            ulong cb1 = br.ReadUInt64(); // unknown. seems constant for all sprites
            if(cb1 != 0xBF795EF4D3FE85C5) sprite.SetAttribute("L0", cb1.ToString("X16"));
            int spriteWidth = br.ReadInt32(), spriteHeight = br.ReadInt32(), xOffset = br.ReadInt16(), yOffset = br.ReadInt16();
            if(xOffset != 0) sprite.SetAttribute("offsetX", xOffset);
            if(yOffset != 0) sprite.SetAttribute("offsetY", yOffset);

            uint f = br.ReadUInt32(); // unknown. flags?
            if(f != 0x6400) sprite.SetAttribute("f", f.ToString("X"));

            ibh = br.ReadBytes(5); // unknown. perhaps a boolean and a float?
            for(int i = 0; i < ibh.Length; i++)
            {
              if(ibh[i] != 0) sprite.SetAttribute("b" + (i+1).ToStringInvariant(), ibh[i]);
            }

            float rotSpeed = br.ReadSingle();
            if(rotSpeed != 0) sprite.SetAttribute("rotSpeed", rotSpeed);

            ibh = br.ReadBytes(4);
            for(int i = 0; i < ibh.Length; i++)
            {
              int defaultValue = i == 0 ? 3 : i == 1 ? 4 : 0;
              if(ibh[i] != defaultValue) sprite.SetAttribute("b" + (i+6).ToStringInvariant(), ibh[i]);
            }

            float f1 = br.ReadSingle(), f2 = br.ReadSingle(); // unknown. almost always zero, but sometimes a small negative number
            if(f1 != 0) sprite.SetAttribute("f1", f1);
            if(f1 != 0) sprite.SetAttribute("f2", f2);

            uint ic = br.ReadUInt32();
            if(ic != 0) sprite.SetAttribute("ic", ic.ToString("X8"));

            float f3 = br.ReadSingle();
            if(f3 != 2) sprite.SetAttribute("f3", f3);

            int frameCount = br.ReadUInt16();
            for(int fi = 0; fi < frameCount; fi++)
            {
              XmlElement frame = frameCount == 1 ? sprite : xml.CreateElement("frame");
              string frameName = ReadString(br);
              Console.WriteLine(frameName);

              int x1 = (int)Math.Round(br.ReadSingle() * imgWidth), x2 = (int)Math.Round(br.ReadSingle() * imgWidth);
              int y1 = (int)Math.Round(br.ReadSingle() * imgHeight), y2 = (int)Math.Round(br.ReadSingle() * imgHeight);
              int storedWidth = x2 - x1, storedHeight = y2 - y1;
              if(storedWidth != spriteWidth || storedHeight != spriteHeight)
              {
                sprite.SetAttribute("width", spriteWidth);
                sprite.SetAttribute("height", spriteHeight);
              }

              frame.SetAttribute("img", frameName);
              float left = br.ReadSingle(), right = br.ReadSingle(), top = br.ReadSingle(), bottom = br.ReadSingle();
              int leftEdge = -(storedWidth+1)/2, rightEdge = storedWidth/2;
              int topEdge = -(storedHeight+1)/2, bottomEdge = storedHeight/2;
              if(left != leftEdge) frame.SetAttribute("left", left);
              if(right != rightEdge) frame.SetAttribute("right", right);
              if(top != topEdge) frame.SetAttribute("top", top);
              if(bottom != bottomEdge) frame.SetAttribute("bottom", bottom);

              using(var fimg = new Bitmap(storedWidth, storedHeight, PixelFormat.Format32bppArgb))
              {
                BitmapData frameBits = fimg.LockBits(new Rectangle(0, 0, storedWidth, storedHeight), ImageLockMode.WriteOnly, fimg.PixelFormat);
                FlipBlit(imgBits, new Rectangle(x1, y1, storedWidth, storedHeight), frameBits, 0, 0);
                fimg.UnlockBits(frameBits);

                string path = Path.Combine(outDir, frameName);
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                fimg.Save(path, ImageFormat.Png);
              }

              if(frame != sprite) sprite.AppendChild(frame);
            }

            ibh = br.ReadBytes(3);
            for(int i = 0; i < ibh.Length; i++)
            {
              if(ibh[i] != 0) sprite.SetAttribute("b" + (i+10).ToStringInvariant(), ibh[i]);
            }

            brush.AppendChild(sprite);
          }

          img.UnlockBits(imgBits);
          xml.Save(Path.Combine(outDir, "metadata.xml"));
        }
      }
    }

    static void PrintUsage()
    {
      Console.WriteLine(@"Usage: bbrusher unpack [<options>] <file.brush> [<outputDirectory>]
  Unpacks all sprites from the image referenced by file.brush into the given
  output directory. If the output directory is not specified, it will be named
  based on the brush file and created in the current directory.

Usage: bbrusher pack [<options>] <file.brush> <inputDirectory>
  Packs all PNG images from the input directory into a sprite sheet and
  creates the file.brush file describing the sprite sheet. The input directory
  must contain an appropriate sprites.xml metadata file describing the images.

Options:
  --gfxPath <directory>
  Specifies the name of the directory where the sprite sheet image should
  loaded from or written to. If omitted, the parent of the directory
  containing the brush file will be used.");
    }

    static unsafe void FlipBlit(BitmapData srcBits, Rectangle srcRect, BitmapData destBits, int destX, int destY)
    {
      byte* src = (byte*)srcBits.Scan0 + (srcRect.Bottom-1)*srcBits.Stride + srcRect.X*4;
      byte* dest = (byte*)destBits.Scan0 + destY*destBits.Stride + destX*4;
      for(int byteWidth = srcRect.Width*4, y = srcRect.Bottom-1; y >= srcRect.Y; src -= srcBits.Stride, dest += destBits.Stride, y--)
      {
        Unsafe.Copy(src, dest, byteWidth);
      }
    }

    static uint GetHex32Attribute(XmlElement el, string attrName, uint defaultValue)
    {
      string str = el.GetAttribute(attrName);
      return string.IsNullOrEmpty(str) ? defaultValue : uint.Parse(str, NumberStyles.HexNumber);
    }

    static ulong GetHex64Attribute(XmlElement el, string attrName, ulong defaultValue)
    {
      string str = el.GetAttribute(attrName);
      return string.IsNullOrEmpty(str) ? defaultValue : ulong.Parse(str, NumberStyles.HexNumber);
    }

    static ulong HashName(string name)
    {
      ulong hash = 0;
      foreach(char c in name) hash = hash*65599 + c;
      return hash;
    }

    static string ReadString(BinaryReader br)
    {
      return Encoding.UTF8.GetString(br.ReadBytes(br.ReadUInt16()));
    }

    static void WriteString(BinaryWriter bw, string str)
    {
      byte[] bytes = Encoding.UTF8.GetBytes(str);
      bw.Write((ushort)bytes.Length);
      bw.Write(bytes);
    }
  }
}
