"use client";

import { useState, useRef } from "react";
import { UploadCloud, FileText, CheckCircle, AlertCircle } from "lucide-react";

interface FileUploadProps {
  onUploadSuccess: (docId: number, title: string) => void;
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const validateAndSetFile = (selectedFile: File) => {
    const ext = selectedFile.name.split(".").pop()?.toLowerCase();
    if (!ext || !["pdf", "docx", "txt"].includes(ext)) {
      setError("Invalid file format. Only PDF, DOCX, and TXT are supported.");
      setFile(null);
      return;
    }
    if (selectedFile.size > 15 * 1024 * 1024) {
      setError("File is too large. Maximum size is 15MB.");
      setFile(null);
      return;
    }
    setError(null);
    setFile(selectedFile);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleUploadSubmit = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setProgress(15);
    
    const formData = new FormData();
    formData.append("file", file);
    
    // Auto populate title
    const docTitle = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
    formData.append("title", docTitle);

    try {
      const token = localStorage.getItem("token");
      setProgress(40);
      
      const response = await fetch("http://localhost:8000/api/v1/upload", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      setProgress(75);
      
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Upload execution failed");
      }

      const docData = await response.json();
      setProgress(100);
      setTimeout(() => {
        onUploadSuccess(docData.id, docData.title);
        setUploading(false);
        setFile(null);
        setProgress(0);
      }, 500);
      
    } catch (err: any) {
      setError(err.message || "An error occurred during file upload.");
      setUploading(false);
    }
  };

  return (
    <div className="w-full flex flex-col gap-4">
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`glass-panel border-2 border-dashed rounded-3xl p-8 flex flex-col items-center justify-center gap-4 cursor-pointer transition-all duration-300 ${
          dragActive
            ? "border-primary bg-primary/5 scale-[1.01]"
            : "border-border hover:border-primary/50 hover:bg-gray-500/5"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFileInput}
          className="hidden"
          disabled={uploading}
        />

        <div className="bg-primary/10 border border-primary/20 text-primary p-4 rounded-full">
          <UploadCloud size={32} className="animate-bounce" />
        </div>

        <div className="text-center">
          <h3 className="text-base font-bold text-foreground">
            Drag & Drop your research paper
          </h3>
          <p className="text-xs text-gray-400 mt-1">
            Accepts PDF, DOCX, and TXT (Maximum 15MB)
          </p>
        </div>
      </div>

      {file && (
        <div className="glass-panel border border-border p-4 rounded-2xl flex items-center justify-between gap-3 animate-fadeIn">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-2.5 rounded-xl">
              <FileText size={20} />
            </div>
            <div>
              <h4 className="text-xs font-semibold text-foreground truncate max-w-[200px] sm:max-w-md">
                {file.name}
              </h4>
              <p className="text-[10px] text-gray-400">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          </div>

          {!uploading ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleUploadSubmit();
              }}
              className="bg-primary hover:bg-primary-hover text-white text-xs font-bold px-4 py-2.5 rounded-xl transition-all shadow-md shadow-primary/15 hover:scale-105"
            >
              Analyze Paper
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-primary animate-pulse">
                Parsing text...
              </span>
            </div>
          )}
        </div>
      )}

      {uploading && (
        <div className="w-full bg-border rounded-full h-2.5 overflow-hidden">
          <div
            className="bg-primary h-full transition-all duration-300 rounded-full"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-2xl flex items-center gap-3 text-xs">
          <AlertCircle size={18} className="shrink-0" />
          <p>{error}</p>
        </div>
      )}
    </div>
  );
}
