"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Upload, Key, Download, Shuffle, FileText, Settings } from "lucide-react";
import { useRouter } from "next/navigation";
import NavButton from "@/components/ui/navButton";

export default function Home() {
  const router = useRouter();
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';
  const [selectedFile, setSelectedFile] = useState(null);
  const [embedFile, setEmbedFile] = useState(null);
  const [key, setKey] = useState("");
  const [outputFile, setOutputFile] = useState(null);
  const [useEncryption, setUseEncryption] = useState(true);
  const [randomEmbedding, setRandomEmbedding] = useState(false);
  const [lsbBits, setLsbBits] = useState(1);
  const [audioUrl, setAudioUrl] = useState(null);
  const [fileName, setFileName] = useState("");
  const [processedFileName, setProcessedFileName] = useState("");
  const [configuration, setConfiguration] = useState(null);
  const [processedAudioUrl, setProcessedAudioUrl] = useState(null);

  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);
  
  useEffect(() => {
    return () => {
      if (processedAudioUrl) {
        URL.revokeObjectURL(processedAudioUrl);
      }
    };
  }, [processedAudioUrl]);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type === "audio/mpeg") {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      setFileName(file?.name)
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setAudioUrl(url);
    } else {
      setFileName('')
      alert("Please select an MP3 file");
      event.target.value = "";
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
        setAudioUrl(null);
      }
    }
  };

  const handleEmbedFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setEmbedFile(file);
    }
  };

  const generateRandomKey = () => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    let result = "";
    for (let i = 0; i < 25; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setKey(result);
  };

  const handleKeyChange = (event) => {
    const value = event.target.value;
    if (value.length <= 25) {
      setKey(value);
    }
  };

  const handleEmbedFile = async () => {
    if (!selectedFile || !embedFile) return;

    try {
      const formData = new FormData();
      formData.append('mp3File', selectedFile);
      formData.append('embedFile', embedFile);
      formData.append('useEncryption', useEncryption.toString());
      formData.append('randomEmbedding', randomEmbedding.toString());
      formData.append('lsbBits', lsbBits.toString());
      
      if ((useEncryption || randomEmbedding) && key) {
        formData.append('key', key);
      }

      console.log("Sending embed request...");
      
      const response = await fetch(`${backendUrl}/encrypt`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success) {
        console.log("Embed successful:", result);
        setOutputFile(selectedFile);
        setProcessedFileName(result.outputFile);
        setConfiguration(result.configuration);
        
        if (result.audioData) {
          try {
            if (processedAudioUrl) {
              URL.revokeObjectURL(processedAudioUrl);
            }
            
            const binaryString = atob(result.audioData);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            
            const audioBlob = new Blob([bytes], { type: result.mimeType || 'audio/mpeg' });
            const newAudioUrl = URL.createObjectURL(audioBlob);
            
            console.log('Created processed audio blob URL:', newAudioUrl);
            console.log('Blob size:', audioBlob.size);
            
            setProcessedAudioUrl(newAudioUrl);
          } catch (error) {
            console.error('Error processing audio data:', error);
            console.error('Base64 data length:', result.audioData?.length);
            alert('Error processing returned audio file: ' + error.message);
          }
        }
      } else {
        console.error("Embed failed:", result.error);
        alert(`Embedding failed: ${result.error}`);
      }
    } catch (error) {
      console.error("Error during embedding:", error);
      alert(`Error during embedding: ${error.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            Audio Steganography Tool
          </h1>
          <p className="text-lg text-slate-600">
            Embed files securely into MP3 audio files
          </p>
          
          <NavButton />
        </div>

        <div className="bg-white rounded-lg shadow-lg p-8 space-y-8">
          <div className="space-y-4">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <Upload className="w-4 h-4" />
              Select MP3 File
            </label>
            <div className="relative">
              <input
                type="file"
                accept=".mp3,audio/mpeg"
                onChange={handleFileChange}
                className="block w-full text-sm text-slate-500 file:mr-4 file:py-3 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 cursor-pointer border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-transparent"
              />
            </div>
            {selectedFile && fileName && (
              <div className="space-y-4">
                <div className="text-sm text-slate-600 bg-slate-50 p-3 rounded-lg">
                  <strong>Selected:</strong> {fileName} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                </div>
                
                {audioUrl && (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center">
                        <svg className="w-4 h-4 text-slate-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.707.707L4.586 13H2a1 1 0 01-1-1V8a1 1 0 011-1h2.586l3.707-3.707a1 1 0 011.09-.217zM15.657 6.343a1 1 0 011.414 0A9.972 9.972 0 0119 12a9.972 9.972 0 01-1.929 5.657 1 1 0 11-1.414-1.414A7.971 7.971 0 0017 12a7.971 7.971 0 00-1.343-4.243 1 1 0 010-1.414z" clipRule="evenodd" />
                          <path fillRule="evenodd" d="M13.829 8.172a1 1 0 011.414 0A5.983 5.983 0 0117 12a5.983 5.983 0 01-1.757 3.828 1 1 0 11-1.414-1.414A3.987 3.987 0 0015 12a3.987 3.987 0 00-1.171-2.828 1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <span className="text-sm font-medium text-slate-700">Audio Preview</span>
                    </div>
                    <audio 
                      key={audioUrl}
                      controls 
                      className="w-full h-10"
                      preload="metadata"
                      style={{
                        outline: 'none',
                        background: 'transparent'
                      }}
                    >
                      <source src={audioUrl} type="audio/mpeg" />
                      Your browser does not support the audio element.
                    </audio>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="space-y-4">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <FileText className="w-4 h-4" />
              File to Embed
            </label>
            <div className="relative">
              <input
                type="file"
                onChange={handleEmbedFileChange}
                className="block w-full text-sm text-slate-500 file:mr-4 file:py-3 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 cursor-pointer border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-transparent"
              />
            </div>
            {embedFile && (
              <div className="text-sm text-slate-600 bg-slate-50 p-3 rounded-lg">
                <strong>Selected:</strong> {embedFile.name} ({(embedFile.size / 1024).toFixed(2)} KB)
              </div>
            )}
          </div>

          <div className="space-y-6 border-t border-slate-200 pt-6">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <Settings className="w-4 h-4" />
              Embedding Options
            </label>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-slate-900">Use Encryption</h4>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="encryption"
                      checked={useEncryption}
                      onChange={() => setUseEncryption(true)}
                      className="w-4 h-4 text-slate-600 border-slate-300 focus:ring-slate-500"
                    />
                    <span className="text-sm text-slate-700">Yes</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="encryption"
                      checked={!useEncryption}
                      onChange={() => setUseEncryption(false)}
                      className="w-4 h-4 text-slate-600 border-slate-300 focus:ring-slate-500"
                    />
                    <span className="text-sm text-slate-700">No</span>
                  </label>
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-sm font-medium text-slate-900">LSB Bits</h4>
                <select
                  value={lsbBits}
                  onChange={(e) => setLsbBits(parseInt(e.target.value))}
                  className="block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-transparent text-sm"
                >
                  <option value={1}>1-bit LSB</option>
                  <option value={2}>2-bit LSB</option>
                  <option value={3}>3-bit LSB</option>
                  <option value={4}>4-bit LSB</option>
                </select>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="text-sm font-medium text-slate-900">Random Embedding Point</h4>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="randomEmbedding"
                    checked={randomEmbedding}
                    onChange={() => setRandomEmbedding(true)}
                    className="w-4 h-4 text-slate-600 border-slate-300 focus:ring-slate-500"
                  />
                  <span className="text-sm text-slate-700">Yes</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="randomEmbedding"
                    checked={!randomEmbedding}
                    onChange={() => setRandomEmbedding(false)}
                    className="w-4 h-4 text-slate-600 border-slate-300 focus:ring-slate-500"
                  />
                  <span className="text-sm text-slate-700">No</span>
                </label>
              </div>
            </div>
          </div>

          {(useEncryption || randomEmbedding) && (
            <div className="space-y-4">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <Key className="w-4 h-4" />
                {useEncryption && randomEmbedding 
                  ? "Encryption Key & Randomization Seed (max 25 characters)"
                  : useEncryption 
                  ? "Encryption Key (max 25 characters)"
                  : "Randomization Seed (max 25 characters)"
                }
              </label>
              <div className="flex gap-3">
                <div className="flex-1 relative">
                  <input
                    type="text"
                    value={key}
                    onChange={handleKeyChange}
                    maxLength={25}
                    placeholder={useEncryption && randomEmbedding 
                      ? "Enter key/seed (used for both encryption and randomization)"
                      : useEncryption 
                      ? "Enter your encryption key"
                      : "Enter your randomization seed"
                    }
                    className="block w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-transparent text-sm"
                  />
                  <div className="absolute right-3 top-3 text-xs text-slate-400">
                    {key.length}/25
                  </div>
                </div>
                <Button
                  onClick={generateRandomKey}
                  variant="outline"
                  size="default"
                  className="px-4 py-3 border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  <Shuffle className="w-4 h-4 mr-2" />
                  Random
                </Button>
              </div>
              {useEncryption && randomEmbedding && (
                <div className="text-sm text-slate-600 bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <strong>Note:</strong> The same string will be used as both the encryption key and the randomization seed.
                </div>
              )}
            </div>
          )}

          <div className="flex justify-center pt-4">
            <Button
              onClick={handleEmbedFile}
              disabled={!selectedFile || !embedFile || ((useEncryption || randomEmbedding) && !key)}
              size="lg"
              className="px-8 py-3 bg-slate-700 hover:bg-slate-800 text-white font-medium disabled:bg-slate-300 disabled:cursor-not-allowed"
            >
              Embed File
            </Button>
          </div>

          <div className="space-y-4 border-t border-slate-200 pt-6">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <Download className="w-4 h-4" />
              Output Result
            </label>
            <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center">
              {outputFile ? (
                <div className="space-y-4">
                  <div className="w-16 h-16 mx-auto bg-slate-100 rounded-lg flex items-center justify-center">
                    <Download className="w-8 h-8 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      Steganography Completed
                    </p>
                    <p className="text-sm text-slate-500 mt-1">
                      File: {processedFileName}
                    </p>
                    
                    {processedAudioUrl && (
                      <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center gap-3 mb-3">
                          <div className="w-8 h-8 bg-green-200 rounded-full flex items-center justify-center">
                            <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.707.707L4.586 13H2a1 1 0 01-1-1V8a1 1 0 011-1h2.586l3.707-3.707a1 1 0 011.09-.217zM15.657 6.343a1 1 0 011.414 0A9.972 9.972 0 0119 12a9.972 9.972 0 01-1.929 5.657 1 1 0 11-1.414-1.414A7.971 7.971 0 0017 12a7.971 7.971 0 00-1.343-4.243 1 1 0 010-1.414z" clipRule="evenodd" />
                              <path fillRule="evenodd" d="M13.829 8.172a1 1 0 011.414 0A5.983 5.983 0 0117 12a5.983 5.983 0 01-1.757 3.828 1 1 0 11-1.414-1.414A3.987 3.987 0 0015 12a3.987 3.987 0 00-1.171-2.828 1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                          </div>
                          <span className="text-sm font-medium text-green-700">Processed Audio Preview</span>
                        </div>
                        <audio 
                          key={processedAudioUrl}
                          controls 
                          className="w-full h-10"
                          preload="metadata"
                          style={{
                            outline: 'none',
                            background: 'transparent'
                          }}
                        >
                          <source src={processedAudioUrl} type="audio/mpeg" />
                          Your browser does not support the audio element.
                        </audio>
                      </div>
                    )}
                    
                    {configuration && (
                      <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-left">
                        <h4 className="text-sm font-semibold text-slate-900 mb-2">Configuration Used:</h4>
                        <div className="space-y-1 text-xs text-slate-600">
                          <div><strong>Original File:</strong> {configuration.originalFileName}</div>
                          <div><strong>Embedded File:</strong> {configuration.embeddedFileName}</div>
                          <div><strong>Use Encryption:</strong> {configuration.useEncryption ? 'Yes' : 'No'}</div>
                          <div><strong>Random Embedding:</strong> {configuration.randomEmbedding ? 'Yes' : 'No'}</div>
                          <div><strong>LSB Bits:</strong> {configuration.lsbBits}-bit</div>
                          <div><strong>PSNR:</strong> {configuration.psnr}</div>
                          {configuration.encryptionKey && (
                            <div><strong>Encryption Key:</strong> {configuration.encryptionKey}</div>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {processedAudioUrl && (
                      <Button
                        onClick={() => {
                          const link = document.createElement('a');
                          link.href = processedAudioUrl;
                          link.download = processedFileName || 'processed_audio.mp3';
                          document.body.appendChild(link);
                          link.click();
                          document.body.removeChild(link);
                        }}
                        variant="outline"
                        size="sm"
                        className="mt-4 border-slate-300 text-slate-700 hover:bg-slate-50"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download Result
                      </Button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-slate-500">
                  <div className="w-16 h-16 mx-auto bg-slate-100 rounded-lg flex items-center justify-center mb-4">
                    <Download className="w-8 h-8 text-slate-400" />
                  </div>
                  <p className="text-sm">
                    Your processed file will appear here after embedding
                  </p>
                </div>
              )}
            </div>
          </div>

        </div>

        <div className="text-center mt-8 text-sm text-slate-500">
          <p>Secure audio steganography with encryption</p>
        </div>
      </div>
    </div>
  );
}
