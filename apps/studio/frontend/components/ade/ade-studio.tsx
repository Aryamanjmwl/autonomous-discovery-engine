'use client'

import { useState } from 'react'
import type { ScreenId } from '@/lib/ade-data'
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
  const [project, setProject] = useState('Manufacturing QC Pipeline')

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-background text-foreground">
      <div className="flex min-h-0 flex-1">
        <Sidebar active={screen} onNavigate={setScreen} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar project={project} onProjectChange={setProject} />
          <main className="min-h-0 flex-1 overflow-y-auto p-6">
            {screen === 'overview' && <OverviewScreen onNavigate={setScreen} />}
            {screen === 'projects' && (
              <ProjectsScreen
                activeProject={project}
                onSelectProject={setProject}
                onNavigate={setScreen}
              />
            )}
            {screen === 'new-analysis' && (
              <NewAnalysisScreen
                activeProject={project}
                onProjectChange={setProject}
                onNavigate={setScreen}
              />
            )}
            {screen === 'runs' && <RunsScreen />}
            {screen === 'findings' && <FindingsScreen />}
            {screen === 'reports' && <ReportsScreen />}
            {screen === 'benchmarks' && <BenchmarksScreen />}
            {screen === 'feedback' && <FeedbackScreen />}
            {screen === 'settings' && <SettingsScreen />}
          </main>
        </div>
      </div>
      <ExecutionStrip />
    </div>
  )
}
