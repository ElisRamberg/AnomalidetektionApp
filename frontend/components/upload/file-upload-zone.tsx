"use client"

import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Card } from "@/components/ui/card"
import { Upload, File, X, CheckCircle, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"

interface UploadedFile {
  file: File
  status: 'uploading' | 'success' | 'error'
  progress: number
  id: string
}

export function FileUploadZone() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isUploading, setIsUploading] = useState(false)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadedFile[] = acceptedFiles.map(file => ({
      file,
      status: 'uploading',
      progress: 0,
      id: Math.random().toString(36).substr(2, 9)
    }))

    setUploadedFiles(prev => [...prev, ...newFiles])
    setIsUploading(true)

    // Simulate upload process
    newFiles.forEach(uploadedFile => {
      simulateUpload(uploadedFile.id)
    })
  }, [])

  const simulateUpload = (fileId: string) => {
    const interval = setInterval(() => {
      setUploadedFiles(prev => 
        prev.map(file => {
          if (file.id === fileId) {
            if (file.progress >= 100) {
              clearInterval(interval)
              setIsUploading(false)
              return { ...file, status: 'success', progress: 100 }
            }
            return { ...file, progress: file.progress + 10 }
          }
          return file
        })
      )
    }, 200)
  }

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== fileId))
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/json': ['.json']
    },
    maxSize: 100 * 1024 * 1024, // 100MB
    multiple: true
  })

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
          isDragActive 
            ? "border-primary bg-primary/5" 
            : "border-muted-foreground/25 hover:border-muted-foreground/50"
        )}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
        {isDragActive ? (
          <p className="text-lg font-medium">Drop the files here...</p>
        ) : (
          <div className="space-y-2">
            <p className="text-lg font-medium">Drag & drop files here</p>
            <p className="text-sm text-muted-foreground">
              or <span className="text-primary underline">browse files</span>
            </p>
            <p className="text-xs text-muted-foreground">
              Supports CSV, Excel, and JSON files up to 100MB
            </p>
          </div>
        )}
      </div>

      {/* Uploaded Files */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-medium">Uploaded Files</h4>
          {uploadedFiles.map((uploadedFile) => (
            <Card key={uploadedFile.id} className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <File className="h-8 w-8 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {uploadedFile.file.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {(uploadedFile.file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  {uploadedFile.status === 'uploading' && (
                    <div className="w-24">
                      <Progress value={uploadedFile.progress} className="h-2" />
                    </div>
                  )}
                  {uploadedFile.status === 'success' && (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  )}
                  {uploadedFile.status === 'error' && (
                    <AlertCircle className="h-5 w-5 text-red-500" />
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(uploadedFile.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              {uploadedFile.status === 'success' && (
                <div className="mt-3 pt-3 border-t">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      Upload completed successfully
                    </span>
                    <Button size="sm" variant="outline">
                      Start Analysis
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
} 