import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { MoreHorizontal, Download, Eye, Trash2 } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface UploadHistoryItem {
  id: string
  filename: string
  uploadDate: string
  status: 'completed' | 'processing' | 'failed'
  size: string
  recordCount: number
  anomaliesFound: number
}

const mockData: UploadHistoryItem[] = [
  {
    id: '1',
    filename: 'transactions_2024_q1.csv',
    uploadDate: '2024-01-15 14:30',
    status: 'completed',
    size: '25.6 MB',
    recordCount: 145234,
    anomaliesFound: 23
  },
  {
    id: '2',
    filename: 'user_activity_jan.xlsx',
    uploadDate: '2024-01-14 09:15',
    status: 'processing',
    size: '12.3 MB',
    recordCount: 89567,
    anomaliesFound: 0
  },
  {
    id: '3',
    filename: 'payment_logs.json',
    uploadDate: '2024-01-13 16:45',
    status: 'completed',
    size: '8.7 MB',
    recordCount: 34521,
    anomaliesFound: 7
  },
  {
    id: '4',
    filename: 'failed_upload.csv',
    uploadDate: '2024-01-12 11:20',
    status: 'failed',
    size: '45.2 MB',
    recordCount: 0,
    anomaliesFound: 0
  }
]

function getStatusBadge(status: UploadHistoryItem['status']) {
  switch (status) {
    case 'completed':
      return <Badge variant="default" className="bg-green-100 text-green-800">Completed</Badge>
    case 'processing':
      return <Badge variant="secondary">Processing</Badge>
    case 'failed':
      return <Badge variant="destructive">Failed</Badge>
    default:
      return <Badge variant="outline">Unknown</Badge>
  }
}

export function UploadHistory() {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>File Name</TableHead>
            <TableHead>Upload Date</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Records</TableHead>
            <TableHead>Anomalies</TableHead>
            <TableHead className="w-[50px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {mockData.map((item) => (
            <TableRow key={item.id}>
              <TableCell className="font-medium">{item.filename}</TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {item.uploadDate}
              </TableCell>
              <TableCell>{getStatusBadge(item.status)}</TableCell>
              <TableCell>{item.size}</TableCell>
              <TableCell>
                {item.recordCount > 0 ? item.recordCount.toLocaleString() : '-'}
              </TableCell>
              <TableCell>
                <div className="flex items-center space-x-2">
                  <span>{item.anomaliesFound}</span>
                  {item.anomaliesFound > 0 && (
                    <Badge variant="outline" className="text-xs px-1 py-0">
                      High
                    </Badge>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="h-8 w-8 p-0">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem>
                      <Eye className="mr-2 h-4 w-4" />
                      View Details
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <Download className="mr-2 h-4 w-4" />
                      Download Report
                    </DropdownMenuItem>
                    <DropdownMenuItem className="text-red-600">
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
} 