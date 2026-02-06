declare module 'latex.js' {
  export function parse(input: string, options?: { generator?: HtmlGenerator }): {
    domFragment(): DocumentFragment;
    stylesAndScripts(baseURL?: string): HTMLElement | null;
  };

  export class HtmlGenerator {
    constructor(options?: { hyphenate?: boolean });
  }
}
