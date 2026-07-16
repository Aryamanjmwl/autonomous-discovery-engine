'use client'

import { useEffect, useState } from 'react'
import type { ScreenId } from '@/lib/ade-data'
import { loadStudioData, type StudioAnalysisResult, type StudioData } from '@/lib/ade-api'
import { Sidebar } from '@/components/ade/sidebar'
import { Topbar } from '@/components/ade/topbar'
import { ExecutionStrip } from '@/components/ade/execution-strip'
import { OverviewScreen } from '@/components/ade/screens/overview'
import { ProjectsScreen } from '@/components/ade/screens/projects'
import { NewAnalysisScreen } from '@/components/ade/screens/new-analysis'
import { RunsScreen } from '@/components/ade/screens/runs'
import { FindingsScreen } from '@/components/ade/screens/findings'
import { ReportsScreen } from '@/components/ade/screens/reports'
import { BenchmarksScreen } from '@/components/ade/screens/benchmarks'
import { FeedbackScreen } from '@/components/ade/screens/feedback'
import { SettingsScreen } from '@/components/ade/screens/settings'

export function AdeStudio() {
  const [screen, setScreen] = useState<ScreenId>('overview')
  const [project, setProject] = useState('ADE Local Engine')
  const [studioData, setStudioData] = useState<StudioData>({
    mode: 'mock',
    health: null,
    summary: null,
    runs: [],
    reports: [],
    selectedReport: null,
    error: null,
  })
  const [analysisResult, setAnalysisResult] = useState<StudioAnalysisResult | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const refreshStudioData = async (reportName?: string) => {
    setIsRefreshing(true)
    try {
      const nextData = await loadStudioData(reportName)
      setStudioData(nextData)
    } finally {
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    void refreshStudioData()
  }, [])

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-background text-foreground">
      <div className="flex min-h-0 flex-1">
        <Sidebar active={screen} onNavigate={setScreen} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar
            project={project}
            onProjectChange={setProject}
            engineMode={studioData.mode}
            health={studioData.health}
            summary={studioData.summary}
            isRefreshing={isRefreshing}
            onRefresh={() => void refreshStudioData(studioData.selectedReport?.report_name)}
          />
          <main className="min-h-0 flex-1 overflow-y-auto p-6">
            {screen === 'overview' && (
              <OverviewScreen
                onNavigate={setScreen}
                studioData={studioData}
                selectedReport={studioData.selectedReport}
              />
            )}
            {screen === 'projects' && (
              <ProjectsScreen
                activeProject={project}
                onSelectProject={setProject}
                onNavigate={setScreen}
                engineMode={studioData.mode}
                summary={studioData.summary}
              />
            )}
            {screen === 'new-analysis' && (
              <NewAnalysisScreen
                activeProject={project}
                onProjectChange={setProject}
                onNavigate={setScreen}
                engineMode={studioData.mode}
                onAnalysisComplete={(result) => {
                  setAnalysisResult(result)
                  void refreshStudioData()
                }}
              />
            )}
            {screen === 'runs' && (
              <RunsScreen
                runsFromApi={studioData.runs}
                analysisResult={analysisResult}
                engineMode={studioData.mode}
              />
            )}
            {screen === 'findings' && (
              <FindingsScreen
                selectedReport={studioData.selectedReport}
                engineMode={studioData.mode}
              />
            )}
            {screen === 'reports' && (
              <ReportsScreen
                reportsFromApi={studioData.reports}
                selectedReport={studioData.selectedReport}
                engineMode={studioData.mode}
                onSelectReport={(reportName) => void refreshStudioData(reportName)}
              />
            )}
            {screen === 'benchmarks' && <BenchmarksScreen engineMode={studioData.mode} />}
            {screen === 'feedback' && <FeedbackScreen studioData={studioData} />}
            {screen === 'settings' && <SettingsScreen />}
          </main>
        </div>
      </div>
      <ExecutionStrip studioData={studioData} />
    </div>
  )
}



