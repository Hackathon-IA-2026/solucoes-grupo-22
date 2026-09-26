import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import {
  Login,
  VerifyEmail,
  Registration,
  ResetPassword,
  ApiErrorWatcher,
  TwoFactorScreen,
  RequestPasswordReset,
} from '~/components/Auth';
import { MarketplaceProvider } from '~/components/Agents/MarketplaceContext';
import AgentMarketplace from '~/components/Agents/Marketplace';
import { OAuthSuccess, OAuthError } from '~/components/OAuth';
import Vitrine, { BuscaIndisponivel, ChatIndisponivel } from '~/components/Coppezip/Vitrine';
import { SITE_ESTATICO } from '~/components/Coppezip/api';
import { AuthContextProvider } from '~/hooks/AuthContext';
import WithRum from '~/lib/rum/WithRum';
import RouteErrorBoundary from './RouteErrorBoundary';
import StartupLayout from './Layouts/Startup';
import LoginLayout from './Layouts/Login';
import dashboardRoutes from './Dashboard';
import ShareRoute from './ShareRoute';
import ChatRoute from './ChatRoute';
import Search from './Search';
import Root from './Root';

const AuthLayout = () => (
  <AuthContextProvider>
    <WithRum>
      <Outlet />
    </WithRum>
    <ApiErrorWatcher />
  </AuthContextProvider>
);

const loadInlinePromptsView = () =>
  import('~/components/Prompts/layouts/InlinePromptsView').then((m) => ({
    Component: m.default,
  }));

const loadSkillsView = () =>
  import('~/components/Skills/layouts/SkillsView').then((m) => ({
    Component: m.default,
  }));

const loadTimelineView = () =>
  import('~/components/Timeline').then((m) => ({
    Component: m.TimelineView,
  }));

const loadProjectsView = () =>
  import('~/components/Projects').then((m) => ({
    Component: m.ProjectsView,
  }));

const loadProjectWorkspace = () =>
  import('~/components/Projects').then((m) => ({
    Component: m.ProjectWorkspace,
  }));

const loadPainelView = () =>
  import('~/components/Coppezip/PainelView').then((m) => ({
    Component: m.default,
  }));

const loadBuscaView = () =>
  import('~/components/Coppezip/BuscaView').then((m) => ({
    Component: m.default,
  }));

const loadGrafoView = () =>
  import('~/components/Coppezip/GrafoView').then((m) => ({
    Component: m.default,
  }));

const baseEl = document.querySelector('base');
const baseHref = baseEl?.getAttribute('href') || '/';

// Vitrine estática (VITE_SITE_ESTATICO=1, ver infra/publicar_site.py): só as abas que leem JSON, fora do portão de
// login, porque num bucket S3 não há /api/config nem sessão. O caminho desconhecido cai no Painel porque o S3 devolve
// o index.html como ErrorDocument.
const rotasEstaticas = [
  {
    path: '/',
    element: <Vitrine />,
    errorElement: <RouteErrorBoundary />,
    children: [
      { index: true, element: <Navigate to="painel" replace={true} /> },
      { path: 'painel', lazy: loadPainelView },
      { path: 'grafo', lazy: loadGrafoView },
      { path: 'timeline', lazy: loadTimelineView },
      { path: 'timeline/:empresaId', lazy: loadTimelineView },
      { path: 'busca', element: <BuscaIndisponivel /> },
      { path: 'c/*', element: <ChatIndisponivel /> },
      { path: '*', element: <Navigate to="painel" replace={true} /> },
    ],
  },
];

const rotasCompletas = [
  {
    path: 'share/:shareId',
    element: <ShareRoute />,
    errorElement: <RouteErrorBoundary />,
  },
  {
    path: 'oauth',
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        path: 'success',
        element: <OAuthSuccess />,
      },
      {
        path: 'error',
        element: <OAuthError />,
      },
    ],
  },
  {
    path: '/',
    element: <StartupLayout />,
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        path: 'register',
        element: <Registration />,
      },
      {
        path: 'forgot-password',
        element: <RequestPasswordReset />,
      },
      {
        path: 'reset-password',
        element: <ResetPassword />,
      },
    ],
  },
  {
    path: 'verify',
    element: <VerifyEmail />,
    errorElement: <RouteErrorBoundary />,
  },
  {
    element: <AuthLayout />,
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        path: '/',
        element: <LoginLayout />,
        children: [
          {
            path: 'login',
            element: <Login />,
          },
          {
            path: 'login/2fa',
            element: <TwoFactorScreen />,
          },
        ],
      },
      dashboardRoutes,
      {
        path: '/',
        element: <Root />,
        children: [
          {
            index: true,
            element: <Navigate to="/c/new" replace={true} />,
          },
          {
            path: 'c/:conversationId?',
            element: <ChatRoute />,
          },
          {
            path: 'search',
            element: <Search />,
          },
          {
            path: 'prompts',
            element: <Navigate to="/prompts/new" replace={true} />,
          },
          {
            path: 'prompts/new',
            lazy: loadInlinePromptsView,
          },
          {
            path: 'prompts/:promptId',
            lazy: loadInlinePromptsView,
          },
          {
            path: 'skills',
            lazy: loadSkillsView,
          },
          {
            path: 'skills/new',
            lazy: loadSkillsView,
          },
          {
            path: 'skills/:skillId',
            lazy: loadSkillsView,
          },
          {
            path: 'skills/:skillId/edit',
            lazy: loadSkillsView,
          },
          {
            path: 'timeline',
            lazy: loadTimelineView,
          },
          {
            path: 'timeline/:empresaId',
            lazy: loadTimelineView,
          },
          {
            path: 'projects',
            lazy: loadProjectsView,
          },
          {
            path: 'projects/:projectId',
            lazy: loadProjectWorkspace,
          },
          {
            path: 'agents',
            element: (
              <MarketplaceProvider>
                <AgentMarketplace />
              </MarketplaceProvider>
            ),
          },
          {
            path: 'agents/:category',
            element: (
              <MarketplaceProvider>
                <AgentMarketplace />
              </MarketplaceProvider>
            ),
          },
          {
            path: 'painel',
            lazy: loadPainelView,
          },
          {
            path: 'busca',
            lazy: loadBuscaView,
          },
          {
            path: 'grafo',
            lazy: loadGrafoView,
          },
        ],
      },
    ],
  },
];

export const router = createBrowserRouter(SITE_ESTATICO ? rotasEstaticas : rotasCompletas, {
  basename: baseHref,
});
