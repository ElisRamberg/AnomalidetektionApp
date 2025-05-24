import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { FileUploadZone } from "@/components/upload/file-upload-zone"
import { UploadHistory } from "@/components/upload/upload-history"
import { UploadStats } from "@/components/upload/upload-stats"
import { Upload, FileText, AlertCircle, CheckCircle } from "lucide-react"

export default function UploadPage() {
  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Data Upload</h2>
          <p className="text-muted-foreground">
            Upload transaction data files for anomaly detection analysis
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline">System Ready</Badge>
        </div>
      </div>

      {/* Upload Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <UploadStats />
      </div>

      {/* Main Upload Area */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* File Upload Zone */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Upload Data File
            </CardTitle>
            <CardDescription>
              Drop your CSV, Excel, or JSON files here to begin analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FileUploadZone />
          </CardContent>
        </Card>

        {/* Upload Requirements */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              File Requirements
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <h4 className="font-medium">Supported Formats</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• CSV files (.csv)</li>
                <li>• Excel files (.xlsx, .xls)</li>
                <li>• JSON files (.json)</li>
              </ul>
            </div>
            
            <div className="space-y-2">
              <h4 className="font-medium">Required Columns</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Transaction ID</li>
                <li>• Amount</li>
                <li>• Timestamp</li>
                <li>• Account ID</li>
              </ul>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium">Limits</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Max file size: 100MB</li>
                <li>• Max rows: 1M transactions</li>
              </ul>
            </div>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                Ensure your data is properly formatted and contains no sensitive information in column headers.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>

      {/* Upload History */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Uploads</CardTitle>
          <CardDescription>
            View your recent file uploads and their processing status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <UploadHistory />
        </CardContent>
      </Card>
    </div>
  )
} 