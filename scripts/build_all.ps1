<#
Build all Dockerfiles recursively.
Usage:
  .\build_all.ps1 [-NoCache]
Examples:
  .\build_all.ps1           # build with cache
  .\build_all.ps1 -NoCache  # force no-cache
#>
param(
  [string]$ImageTag = 'latest',
  [switch]$NoCache
)

$root = (Get-Location).Path

Write-Host "Procurando Dockerfiles..."
$files = Get-ChildItem -Path $root -Recurse -Filter Dockerfile -File
if (-not $files) {
    Write-Host "Nenhum Dockerfile encontrado." -ForegroundColor Yellow
    exit 0
}

foreach ($f in $files) {
    $context = Split-Path $f.FullName -Parent
    # gerar tag baseada no caminho relativo (replace \ e / por -)
    $rel = $null
    if ($context.Length -gt $root.Length) {
      $rel = $context.Substring($root.Length).TrimStart('\','/')
    }
    if ([string]::IsNullOrEmpty($rel)) {
      # usar nome da pasta do repositório como tag para o contexto raiz
      $tag = (Split-Path $root -Leaf).ToLower()
    } else {
      $tag = ($rel -replace '[\\/\s]+','-').ToLower()
    }
    # limpar caracteres inválidos no início/fim
    $tag = $tag.TrimStart('.','-')
    $tag = $tag.Trim()
    if ([string]::IsNullOrEmpty($tag)) { $tag = 'image' }

    $noCacheArg = ""
    if ($NoCache) { $noCacheArg = "--no-cache" }
    $fullTag = "$($tag):$($ImageTag)"

    Write-Host "\nBuilding: $f (context: $context) -> tag: $fullTag"
    $cmd = "docker build $noCacheArg -t `"$($fullTag)`" -f `"$($f.FullName)`" `"$context`""
    Write-Host "> $cmd"
    $exit = Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Build falhou para $f" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "\nBuilds completos." -ForegroundColor Green
