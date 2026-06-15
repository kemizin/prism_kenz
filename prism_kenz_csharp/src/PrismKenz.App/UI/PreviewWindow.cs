using OpenCvSharp;

namespace PrismKenz.App.UI;

public sealed class PreviewWindow : IDisposable
{
    private const string WindowName = "Prism Kenz C# Preview";

    public PreviewWindow()
    {
        Cv2.NamedWindow(WindowName, WindowFlags.Normal);
    }

    public bool Show(Mat frame, double fps)
    {
        using var preview = frame.Clone();
        Cv2.PutText(
            preview,
            $"FPS: {fps:0.0} | Q/ESC sair",
            new Point(20, 35),
            HersheyFonts.HersheySimplex,
            0.8,
            Scalar.White,
            2,
            LineTypes.AntiAlias);

        Cv2.ImShow(WindowName, preview);
        var key = Cv2.WaitKey(1);
        return key is 27 or 'q' or 'Q';
    }

    public void Dispose()
    {
        Cv2.DestroyWindow(WindowName);
    }
}
