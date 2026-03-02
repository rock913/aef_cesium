import { createApp } from 'vue'
import AlphaEarthApp from './App.vue'
import Zero2xApp from './Zero2xApp.vue'

const rawPath = String(window.location.pathname || '/')
const path = rawPath.replace(/\/+$/, '') || '/'
const isDemo = path === '/demo'
const isWorkbench = path === '/workbench'
const isAct2 = path === '/act2'

try {
	document.body.style.overflow = (isDemo || isWorkbench || isAct2) ? 'hidden' : 'auto'
} catch (_) {
	// ignore
}

async function bootstrap() {
	if (isDemo) {
		createApp(AlphaEarthApp).mount('#app')
		return
	}

	if (isWorkbench) {
		try {
			const mod = await import('./WorkbenchApp.vue')
			const WorkbenchApp = mod?.default ?? mod
			createApp(WorkbenchApp).mount('#app')
			return
		} catch (e) {
			// Fallback to landing if the workbench chunk fails.
			console.error('Failed to load workbench:', e)
		}
	}

	if (isAct2) {
		try {
			const mod = await import('./Act2App.vue')
			const Act2App = mod?.default ?? mod
			createApp(Act2App).mount('#app')
			return
		} catch (e) {
			console.error('Failed to load act2:', e)
		}
	}

	createApp(Zero2xApp).mount('#app')
}

bootstrap()
