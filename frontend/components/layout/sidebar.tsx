"use client"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { AlertTriangle, BarChart3, GitBranch, LayoutDashboard, Settings, Table, Upload } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Transactions", href: "/transactions", icon: Table },
  { name: "Group Analysis", href: "/group-analysis", icon: BarChart3 },
  { name: "Correlations", href: "/correlations", icon: GitBranch },
  { name: "Upload Data", href: "/upload", icon: Upload },
  { name: "Strategy Editor", href: "/strategy", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="flex flex-col w-64 bg-card border-r">
      <div className="flex items-center h-16 px-4 border-b">
        <AlertTriangle className="h-8 w-8 text-primary" />
        <span className="ml-2 text-lg font-semibold">AnomalyDetect</span>
      </div>
      <nav className="flex-1 px-2 py-4 space-y-2">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link key={item.name} href={item.href}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className={cn("w-full justify-start", isActive && "bg-secondary")}
              >
                <item.icon className="mr-2 h-4 w-4" />
                {item.name}
              </Button>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
