'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ExternalLink, Download, Code2 } from 'lucide-react'

export default function ApiExplorerPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-12 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">API Explorer</h1>
        <p className="mt-4 text-lg text-muted-foreground">Interactive API documentation with try-it-now functionality.</p>
      </div>
      <div className="mx-auto max-w-4xl">
        <Tabs defaultValue="swagger">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="swagger">Swagger UI</TabsTrigger>
            <TabsTrigger value="redoc">Redoc</TabsTrigger>
            <TabsTrigger value="openapi">OpenAPI Spec</TabsTrigger>
          </TabsList>
          <TabsContent value="swagger">
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><Code2 className="h-5 w-5" /> Swagger UI</CardTitle></CardHeader>
              <CardContent>
                <p className="mb-4 text-sm text-muted-foreground">
                  Interactive API documentation with request/response examples and try-it-now functionality.
                </p>
                <div className="rounded-lg border bg-muted p-8 text-center">
                  <p className="text-muted-foreground">Swagger UI loads from <code className="text-sm">/openapi.json</code></p>
                  <Button className="mt-4" asChild>
                    <a href="/openapi.json" target="_blank" rel="noopener noreferrer">
                      Open Swagger UI <ExternalLink className="ml-2 h-4 w-4" />
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="redoc">
            <Card>
              <CardHeader><CardTitle>Redoc</CardTitle></CardHeader>
              <CardContent>
                <p className="mb-4 text-sm text-muted-foreground">
                  Clean, three-panel API documentation optimized for readability.
                </p>
                <div className="rounded-lg border bg-muted p-8 text-center">
                  <Button asChild><a href="/redoc" target="_blank" rel="noopener noreferrer">Open Redoc <ExternalLink className="ml-2 h-4 w-4" /></a></Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="openapi">
            <Card>
              <CardHeader><CardTitle>OpenAPI Specification</CardTitle></CardHeader>
              <CardContent>
                <p className="mb-4 text-sm text-muted-foreground">
                  Download the raw OpenAPI 3.1 JSON specification for code generation and tooling.
                </p>
                <div className="flex gap-4">
                  <Button asChild><a href="/openapi.json" download><Download className="mr-2 h-4 w-4" /> Download JSON</a></Button>
                  <Button variant="outline" asChild><a href="/openapi.yaml" download><Download className="mr-2 h-4 w-4" /> Download YAML</a></Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
        <Card className="mt-8">
          <CardHeader><CardTitle>Authentication</CardTitle></CardHeader>
          <CardContent>
            <p className="mb-2 text-sm text-muted-foreground">All API requests require a Bearer token:</p>
            <pre className="rounded-lg bg-muted p-4"><code className="text-sm font-mono">Authorization: Bearer your-api-key</code></pre>
            <p className="mt-4 text-sm text-muted-foreground">Get your API key from <a href="/portal/api-keys" className="text-blue-600 underline">API Keys settings</a>.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
