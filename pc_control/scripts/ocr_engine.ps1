# Windows OCR via WinRT
param(
    [Parameter(Mandatory=$true)][string]$ImagePath,
    [string]$Language = "es"
)

$ErrorActionPreference = "Stop"

# Load WinRT
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.RandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime]

# Async helper
Add-Type -Language CSharp @"
using System;
using System.Threading.Tasks;
using System.Runtime.CompilerServices;

public static class AsyncHelper {
    public static T RunSync<T>(Windows.Foundation.IAsyncOperation<T> op) {
        var task = System.WindowsRuntimeSystemExtensions.AsTask(op);
        task.Wait();
        return task.Result;
    }
}
"@ -ReferencedAssemblies @(
    "System.Runtime.WindowsRuntime",
    [Windows.Media.Ocr.OcrEngine].Assembly.Location,
    [Windows.Graphics.Imaging.BitmapDecoder].Assembly.Location,
    [Windows.Storage.StorageFile].Assembly.Location
)

try {
    $absPath = (Resolve-Path $ImagePath).Path

    # Open file
    $fileOp = [Windows.Storage.StorageFile]::GetFileFromPathAsync($absPath)
    $file = [AsyncHelper]::RunSync($fileOp)

    # Open stream
    $streamOp = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
    $stream = [AsyncHelper]::RunSync($streamOp)

    # Decode image
    $decoderOp = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
    $decoder = [AsyncHelper]::RunSync($decoderOp)

    $bitmapOp = $decoder.GetSoftwareBitmapAsync()
    $bitmap = [AsyncHelper]::RunSync($bitmapOp)

    # Create OCR engine
    $lang = [Windows.Globalization.Language]::new($Language)
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)

    if ($null -eq $engine) {
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    }

    if ($null -eq $engine) {
        Write-Error "OCR not available"
        exit 1
    }

    # Run OCR
    $ocrOp = $engine.RecognizeAsync($bitmap)
    $result = [AsyncHelper]::RunSync($ocrOp)

    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $result.Text

    $stream.Dispose()
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
