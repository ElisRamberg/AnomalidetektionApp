import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { StrategyPresets } from "@/components/strategy/strategy-presets"
import { ParameterEditor } from "@/components/strategy/parameter-editor"
import { StrategyPreview } from "@/components/strategy/strategy-preview"

export default function StrategyPage() {
  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Strategy Editor</h2>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Strategy Presets</CardTitle>
            <CardDescription>Choose from predefined detection strategies</CardDescription>
          </CardHeader>
          <CardContent>
            <StrategyPresets />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Parameter Editor</CardTitle>
            <CardDescription>Fine-tune detection parameters</CardDescription>
          </CardHeader>
          <CardContent>
            <ParameterEditor />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Strategy Preview</CardTitle>
            <CardDescription>Preview impact of strategy changes</CardDescription>
          </CardHeader>
          <CardContent>
            <StrategyPreview />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
