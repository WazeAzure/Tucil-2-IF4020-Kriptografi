"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Upload, Key, Download, Shuffle, FileText, Settings, Loader2, AlertTriangle } from "lucide-react";
import { useRouter } from "next/navigation";
import NavButton from "@/components/ui/navButton";
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function Decrypt() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState(null);
  const [key, setKey] = useState("");
  const [extractedFile, setExtractedFile] = useState(null);
  const [useEncryption, setUseEncryption] = useState(true);
  const [randomEmbedding, setRandomEmbedding] = useState(false);
  const [lsbBits, setLsbBits] = useState(1);
  const [configuration, setConfiguration] = useState(null);
  const [extractedFileUrl, setExtractedFileUrl] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [fileName, setFileName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorDialog, setErrorDialog] = useState({ open: false, title: "", message: "" });
  const [extractedFileHash, setExtractedFileHash] = useState("");
  const [expectedHash, setExpectedHash] = useState("");
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

  const showError = (title, message) => {
    setErrorDialog({ open: true, title, message });
  };

  const calculateSHA256 = async (blob) => {
    try {
      const arrayBuffer = await blob.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      return hashHex;
    } catch (error) {
      console.error('Error calculating SHA-256:', error);
      return 'Error calculating hash';
    }
  };

  const verifyIntegrity = (actualHash, expectedHash) => {
    if (!expectedHash || !actualHash) return null;
    return actualHash.toLowerCase() === expectedHash.toLowerCase();
  };

  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type === "audio/mpeg") {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      setFileName(file?.name);
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setAudioUrl(url);
      toast.success('MP3 file uploaded successfully!');
    } else {
      setFileName('');
      showError("Invalid File Type", "Please select an MP3 file. Only audio/mpeg files are supported.");
      event.target.value = "";
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
        setAudioUrl(null);
      }
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

  const handleExtractFile = async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('mp3File', selectedFile);
      formData.append('useEncryption', useEncryption.toString());
      formData.append('randomEmbedding', randomEmbedding.toString());
      formData.append('lsbBits', lsbBits.toString());
      
      if ((useEncryption || randomEmbedding) && key) {
        formData.append('key', key);
      }

      console.log("Sending decrypt request...");
      
      const response = await fetch(`${backendUrl}/decrypt`, {
        method: 'POST',
        body: formData,
      });

      let result;
      try {
        result = await response.json();
      } catch (parseError) {
        console.error('Error parsing response:', parseError);
        throw new Error(`Server returned invalid response (Status: ${response.status})`);
      }

      if (!response.ok) {
        const errorMessage = result?.error || result?.message || `Server error (Status: ${response.status})`;
        throw new Error(errorMessage);
      }
      
      if (result.success) {
        console.log("Decrypt successful:", result);
        setConfiguration(result.configuration);
        toast.success('File extracted successfully!');
        
        if (result.extractedFileData) {
          try {
            const binaryString = atob(result.extractedFileData);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            
            const fileBlob = new Blob([bytes], { type: result.mimeType || 'text/plain' });
            const fileUrl = URL.createObjectURL(fileBlob);
            const hash = await calculateSHA256(fileBlob);
            
            setExtractedFile({
              name: result.extractedFileName,
              size: fileBlob.size,
              type: result.mimeType || 'text/plain'
            });
            setExtractedFileUrl(fileUrl);
            setExtractedFileHash(hash);
          } catch (error) {
            console.error('Error processing extracted file data:', error);
            showError('File Processing Error', `Error processing extracted file: ${error.message}`);
          }
        }
      } else {
        const errorMessage = result.error || result.message || 'Unknown error occurred during decryption';
        console.error("Decrypt failed:", errorMessage);
        showError('Decryption Failed', errorMessage);
      }
    } catch (error) {
      console.error("Error during decryption:", error);
      showError('Decryption Error', error.message || 'An unexpected error occurred during decryption');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            Audio Steganography Decrypt
          </h1>
          <p className="text-lg text-slate-600">
            Extract hidden files from MP3 audio files
          </p>
          
          <NavButton />
        </div>

        <div className="bg-white rounded-lg shadow-lg p-8 space-y-8">
          <div className="space-y-4">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <Upload className="w-4 h-4" />
              Select MP3 File with Hidden Data
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
                      <span className="text-sm font-medium text-slate-700">Embedded Audio Preview</span>
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



          <div className="space-y-6 border-t border-slate-200 pt-6">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <Settings className="w-4 h-4" />
              Decryption Options
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
                  ? "Decryption Key & Randomization Seed (max 25 characters)"
                  : useEncryption 
                  ? "Decryption Key (max 25 characters)"
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
                      ? "Enter key/seed (used for both decryption and randomization)"
                      : useEncryption 
                      ? "Enter your decryption key"
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
                  <strong>Note:</strong> The same string will be used as both the decryption key and the randomization seed.
                </div>
              )}
            </div>
          )}

          {/* Expected SHA-256 Hash Section */}
          <div className="space-y-4 border-t border-slate-200 pt-6">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <svg className="w-4 h-4 text-slate-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Expected SHA-256 Hash (Optional)
            </label>
            <div className="relative">
              <input
                type="text"
                value={expectedHash}
                onChange={(e) => setExpectedHash(e.target.value.trim())}
                placeholder="Enter expected SHA-256 hash for integrity verification (optional)"
                className="block w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-transparent text-sm font-mono"
              />
            </div>
            {expectedHash && (
              <div className="text-xs text-slate-500 bg-blue-50 border border-blue-200 rounded-lg p-3">
                <strong>Note:</strong> This hash will be compared with the extracted file&apos;s SHA-256 to verify integrity.
              </div>
            )}
          </div>

          {/* Extract Button */}
          <div className="flex justify-center pt-4">
            <Button
              onClick={handleExtractFile}
              disabled={!selectedFile || ((useEncryption || randomEmbedding) && !key) || isLoading}
              size="lg"
              className="px-8 py-3 bg-slate-700 hover:bg-slate-800 text-white font-medium disabled:bg-slate-300 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Extracting...
                </>
              ) : (
                "Extract File"
              )}
            </Button>
          </div>

          {/* Embedded File Output Section */}
          <div className="space-y-4 border-t border-slate-200 pt-6">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <FileText className="w-4 h-4" />
              Embedded File
            </label>
            <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center">
              {extractedFile ? (
                <div className="space-y-4">
                  <div className="w-16 h-16 mx-auto bg-slate-100 rounded-lg flex items-center justify-center">
                    <FileText className="w-8 h-8 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      File Extracted Successfully
                    </p>
                    <p className="text-sm text-slate-500 mt-1">
                      File: {extractedFile.name}
                    </p>
                    <p className="text-sm text-slate-500">
                      Size: {(extractedFile.size / 1024).toFixed(2)} KB
                    </p>
                    
                    {extractedFileHash && (
                      <div className="mt-3 text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <svg className="w-3 h-3 text-slate-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          <strong>File Integrity (SHA-256):</strong>
                        </div>
                        <code className="font-mono text-xs break-all bg-white px-2 py-1 rounded border">
                          {extractedFileHash}
                        </code>
                      </div>
                    )}
                    
                    {expectedHash && extractedFileHash && (
                      <div className={`mt-3 text-xs rounded-lg p-3 border ${
                        verifyIntegrity(extractedFileHash, expectedHash) 
                          ? 'bg-green-50 border-green-200 text-green-700' 
                          : 'bg-red-50 border-red-200 text-red-700'
                      }`}>
                        <div className="flex items-center gap-2 mb-1">
                          {verifyIntegrity(extractedFileHash, expectedHash) ? (
                            <svg className="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                          ) : (
                            <svg className="w-3 h-3 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                          )}
                          <strong>Integrity Verification:</strong>
                        </div>
                        <div className="text-xs">
                          {verifyIntegrity(extractedFileHash, expectedHash) 
                            ? '✅ File integrity verified! The extracted file matches the expected hash.' 
                            : '❌ File integrity check failed! The extracted file does not match the expected hash.'}
                        </div>
                        <div className="mt-2 text-xs opacity-75">
                          <strong>Expected:</strong> <code className="font-mono bg-white px-1 py-0.5 rounded">{expectedHash}</code>
                        </div>
                      </div>
                    )}
                    
                    {configuration && (
                      <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-left">
                        <h4 className="text-sm font-semibold text-slate-900 mb-2">Configuration Used:</h4>
                        <div className="space-y-1 text-xs text-slate-600">
                          <div><strong>File Extension:</strong> {configuration.fileExtension}</div>
                          <div><strong>File Name:</strong> {configuration.fileName}</div>
                          <div><strong>Use Encryption:</strong> {configuration.useEncryption ? 'Yes' : 'No'}</div>
                          <div><strong>Random Embed Point:</strong> {configuration.randomEmbedPoint ? 'Yes' : 'No'}</div>
                          <div><strong>LSB Bits:</strong> {configuration.lsbBits}-bit</div>
                        </div>
                      </div>
                    )}
                    
                    {extractedFileUrl && (
                      <Button
                        onClick={() => {
                          const link = document.createElement('a');
                          link.href = extractedFileUrl;
                          link.download = extractedFile.name || 'extracted_file.txt';
                          document.body.appendChild(link);
                          link.click();
                          document.body.removeChild(link);
                        }}
                        variant="outline"
                        size="sm"
                        className="mt-4 border-slate-300 text-slate-700 hover:bg-slate-50"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download File
                      </Button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-slate-500">
                  <div className="w-16 h-16 mx-auto bg-slate-100 rounded-lg flex items-center justify-center mb-4">
                    <FileText className="w-8 h-8 text-slate-400" />
                  </div>
                  <p className="text-sm">
                    The extracted file will appear here after decryption
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="text-center mt-8 text-sm text-slate-500">
          <p>Decrypt and extract hidden files from audio steganography</p>
        </div>
      </div>
      
      {/* Error Dialog */}
      <Dialog open={errorDialog.open} onOpenChange={(open) => setErrorDialog({ ...errorDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              {errorDialog.title}
            </DialogTitle>
            <DialogDescription className="text-slate-600 mt-2">
              {errorDialog.message}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button 
              onClick={() => setErrorDialog({ open: false, title: "", message: "" })}
              className="bg-slate-700 hover:bg-slate-800 text-white"
            >
              OK
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
    </div>
  );
}
