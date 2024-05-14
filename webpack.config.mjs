import path from 'path';
const __dirname = path.dirname(new URL(import.meta.url).pathname);
const __filename = new URL(import.meta.url).pathname;
//const { CleanWebpackPlugin } = require('clean-webpack-plugin');
import * as marked from 'marked';
import webpack from 'webpack';
import HtmlWebpackPlugin from 'html-webpack-plugin';
import FaviconsWebpackPlugin from 'favicons-webpack-plugin';
import MiniCssExtractPlugin from 'mini-css-extract-plugin';
//import HotModuleReplacementPlugin from 'webpack/lib/HotModuleReplacementPlugin';
const renderer = new marked.Renderer();
const hmrp = new webpack.HotModuleReplacementPlugin();
const isDevServer = process.env.WEBPACK_SERVE;

const config = {
    mode: 'development',
    target: 'web',
    context: path.resolve(__dirname, 'puffin'),
    plugins: [
        new MiniCssExtractPlugin({ filename: '[name].css' }),
        //new FaviconsWebpackPlugin('../static/assets/puffin_red.svg'),
        new HtmlWebpackPlugin({
            filename: 'templates/index.html',
            template: '../templates/page.html',
            publicPath: '',
            minify: false
        }),
        new HtmlWebpackPlugin({
            filename: 'templates/login.html',
            template: '../templates/login.html',
            publicPath: '..',
            minify: false
        }),
    ],
    stats: {
        loggingDebug: ['sass-loader'],
    },
    entry: {
        //html: { import: '../static/index.html' },
        bundle: ['./app/index.ts'], //{
        /* import: [
                './app/index.mts', 
                            './css/style.scss',
               /* './css/common.scss',
                './css/editor.scss',
                './css/buttons.scss',
                './css/frames.scss',
                './css/markdown.scss',
                './css/terminal.scss',
                './css/grid-display.scss',*/
        // ],*/
        //filename: 'js/bundle.js',
        //},
        // path.join(__dirname, 'src', 'main', 'webroot','css', 'style.scss'),
        //html: ['./webroot/terms-no.md'],
    },
    output: {
        path: path.resolve(__dirname, 'dist', 'webroot'),
        //    publicPath: 'static/',
        filename: 'static/js/[name].[contenthash].js',
        clean: true,
    },
    devServer: {
        port: 7778,
        static: [
            path.resolve(__dirname, 'dist', 'webroot'),
            {
                directory: path.resolve(__dirname, 'static'),
                publicPath: '/static',
            },
            {
                directory: path.resolve(__dirname, '..', 'turtleduck', 'fonts'),
                publicPath: '/static/fonts',
            },
        ],
        hot: 'only',
        liveReload: false,
        magicHtml: false,
        historyApiFallback: {
            rewrites: [{ from: /^\/~/, to: '/index.html' }],
            //verbose: true,
        },
        devMiddleware: {
            writeToDisk: true,
        },
        // (use symlink) watchFiles: ['../borb/**/*.ts', '../borb/**/*.js']
    },
    resolve: {
        extensions: ['.ts', '.mts', '.tsx', '.js', '.mjs'],
        symlinks: false,
        alias: {
            //          'borb$': path.resolve(__dirname, 'src/main/webroot/borb/borb'),
            //        'borb': path.resolve(__dirname, 'src/main/webroot/borb'),
            //        '../../../../borb/src/Styles.ts$': path.resolve(__dirname, '../borb/src/Styles.ts'),
            //      '../../../../borb/src': path.resolve(__dirname, '../borb/src')
        },
        fallback: { path: 'path-browserify' },
        //  fallback: {
        //      "querystring": require.resolve("querystring-es3/"),
        //      "buffer": require.resolve("buffer/")
        //  }
    },
    optimization: {
        usedExports: true,
    },
    cache: {
        type: 'filesystem',
        cacheDirectory: path.resolve(
            __dirname,
            `node_modules/.cache/webpack${isDevServer ? '-serve' : ''}`,
        ),
        buildDependencies: { config: [__filename, path.resolve(__dirname, 'tsconfig.json')] },
    },
    module: {
        rules: [
            {
                test: /\.m?tsx?$/,
                loader: 'ts-loader',
            },
            {
                resourceQuery: /raw/,
                type: 'asset/source',
            },
            {
                test: /\.md$/,
                type: 'asset/resource',
                generator: {
                    filename: '[name].html',
                },
                use: [
                    //{ loader: 'file-loader', options: { name: '[name].html', publicPath: '' } },
                    //{ loader: 'extract-loader', options: {} },
                    {
                        loader: 'html-loader',
                        options: {
                            sources: {
                                list: [
                                    { tag: 'img', attribute: 'src', type: 'src' },
                                    { tag: 'link', attribute: 'href', type: 'src' },
                                    //  { tag: 'script', attribute: 'src', type: 'src' },
                                ],
                            },
                        },
                    },
                    {
                        loader: 'markdown-loader',
                        options: {
                            pedantic: false,
                            renderer: renderer,
                        },
                    },
                ],
            },
            {
                test: /\.css$/,
                type: 'asset/resource',
                generator: {
                    filename: '[path][name][ext]',
                },
                use: [
                    process.env.NODE_ENV !== 'production'
                        ? // embeds CSS-as-JS in a style element
                          { loader: 'style-loader', options: { injectType: 'styleTag' } } //'style-loader'
                        : // turns the JS code back into CSS for file output
                          MiniCssExtractPlugin.loader,
                    // turns CSS code into JS (to be inserted at import site),
                    'css-loader',
                ],
            },
            {
                test: /\.txt$/,
                type: 'asset/source',
                //use: [{ loader: 'raw-loader' }],
            },
            {
                test: /\.ne$/,
                use: ['nearley-loader'],
            },
            /*      {
                test: /\.s[ac]ss$/i,
                resourceQuery: { not: [/raw/] },
                //type: 'asset/resource',
                 generator: {
                     filename: '[path][name][ext]',
                 },
                exclude: /node_modules/,
                use: [
                    process.env.NODE_ENV !== 'production'
                    // embeds CSS-as-JS in a style element
                       ? { loader: "style-loader", options: { injectType: "styleTag" } }//'style-loader'
                       // turns the JS code back into CSS for file output
                       : MiniCssExtractPlugin.loader,
                       // turns CSS code into JS (to be inserted at import site)
                   'css-loader',
                    // turns SCSS code into CSS
                    'sass-loader'
                ],
            },*/
            {
                test: /\.s[ac]ss$/i,
                resourceQuery: { not: [/raw/] },
                type: 'asset/resource',
                generator: {
                    filename: 'static/css/[name].css',
                },
                exclude: /node_modules/,
                use: [
                    // turns SCSS code into CSS
                    'sass-loader',
                ],
            },
            {
                test: /\.(png|jpg|gif|svg|eot|ttf|woff|woff2)$/,
                type: 'asset',
                /*                options: {
                    limit: 200000,
                    outputPath: 'static',
                },*/
            },
        ],
    },
};

export default function init(env, argv) {
    config.mode = argv.mode || 'development';
    console.log("MODE: ", config.mode);
    if(config.mode === 'development') {
        config.devtool = 'source-map'
    } else if(config.mode === 'production') {
        config.output.path = path.resolve(__dirname, 'prod-dist', 'webroot')
        config.devtool = 'source-map';
        //config.optimization.minimize = false;
        config.devServer = undefined;
    }
    return config;
}

//export default init;
