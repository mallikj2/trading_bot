declare namespace JSX {
  interface IntrinsicElements { [elemName: string]: any }
}
declare module 'react' {
  export const StrictMode: any;
  export function useEffect(effect: () => void | (() => void), deps: unknown[]): void;
  export function useMemo<T>(factory: () => T, deps: unknown[]): T;
  export function useState<T>(initial: T): [T, (value: T) => void];
}
declare module 'react/jsx-runtime' { export const jsx: any; export const jsxs: any; export const Fragment: any; }
declare module 'react-dom/client' { export function createRoot(node: Element): { render(child: any): void }; }
declare module 'vite' { export function defineConfig(value: any): any; }
