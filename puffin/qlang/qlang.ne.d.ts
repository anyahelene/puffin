//declare module 'qlang.ne' {
    export interface NearleyToken {
        value: any;
        [key: string]: any;
    }
    export interface NearleyLexer {
        reset: (chunk: string, info: any) => void;
        next: () => NearleyToken | undefined;
        save: () => any;
        formatError: (token: never) => string;
        has: (tokenType: string) => boolean;
    }
    export interface NearleyRule {
        name: string;
        symbols: NearleySymbol[];
        postprocess?: (d: any[], loc?: number, reject?: {}) => any;
    }
    export type NearleySymbol =
        | string
        | {
              literal: any;
          }
        | {
              test: (token: any) => boolean;
          };
    export interface Grammar {
        Lexer: NearleyLexer | undefined;
        ParserRules: NearleyRule[];
        ParserStart: string;
    }
    export const grammar: Grammar;
    export default grammar;
//}
