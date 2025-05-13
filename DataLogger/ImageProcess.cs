using OpenCvSharp;
using System;
using System.Collections.Generic;
using System.Diagnostics.Eventing.Reader;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;

namespace DataLogger
{
    static class ImageProcess
    {
        public static Mat BufferToMat(byte[] Buffer, double Scale = 1)
        {
            int w = (int)Math.Sqrt((double)Buffer.Length);
            Mat img = new Mat(w, w, MatType.CV_8UC1);
            Marshal.Copy(Buffer, 0, img.Data, w * w);
            Cv2.Resize(img, img, new OpenCvSharp.Size(w * Scale, w * Scale));
            return img;
        }

        public static void SaveImage(Mat image, string filePath)
        {
            Cv2.ImWrite(filePath, image);
        }
    }
}
