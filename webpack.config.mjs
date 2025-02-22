import path from 'path';
const __dirname = path.dirname(new URL(import.meta.url).pathname);
const __filename = new URL(import.meta.url).pathname;
//const { CleanWebpackPlugin } = require('clean-webpack-plugin');
import * as marked from 'marked';
import webpack from 'webpack';
import HtmlWebpackPlugin from 'html-webpack-plugin';
import FaviconsWebpackPlugin from 'favicons-webpack-plugin';
import CopyPlugin from 'copy-webpack-plugin';
import MiniCssExtractPlugin from 'mini-css-extract-plugin';
//import HotModuleReplacementPlugin from 'webpack/lib/HotModuleReplacementPlugin';
const renderer = new marked.Renderer();
const hmrp = new webpack.HotModuleReplacementPlugin();
const isDevServer = process.env.WEBPACK_SERVE;

const copyPlugin = new CopyPlugin({
    patterns: [
        { context: '../static', from: '*', to: './' },
        { context: '../static', from: '*/**/*', to: 'static/' },
        { context: '../staticfoo', from: '*/**/*', to: 'static/', noErrorOnMissing: true },
    ],
});

const config = {
    mode: 'development',
    target: 'web',
    context: path.resolve(__dirname, 'puffin'),
    experiments: { css: true },
    plugins: [
        new MiniCssExtractPlugin({ filename: '[name].css' }),
        new FaviconsWebpackPlugin({
            logo: '../static/img/puffin_red.svg',
            //logo: '../static/img/puffin-cube.png',
            outputPath: 'static/img',
            favicons: {
                icons: {
                    android: false, // Create Android homescreen icon. `boolean` or `{ offset, background }` or an array of sources
                    appleIcon: false, // Create Apple touch icons. `boolean` or `{ offset, background }` or an array of sources
                    appleStartup: false, // Create Apple startup images. `boolean` or `{ offset, background }` or an array of sources
                    favicons: true, // Create regular favicons. `boolean` or `{ offset, background }` or an array of sources
                    windows: false, // Create Windows 8 tile icons. `boolean` or `{ offset, background }` or an array of sources
                    yandex: false,
                },
            },
        }),
        new HtmlWebpackPlugin({
            filename: 'templates/index.html',
            template: '../templates/page.html',
            publicPath: '',
            inject: false,
            minify: false,
        }),
        new HtmlWebpackPlugin({
            filename: 'templates/login.html',
            template: '../templates/login.html',
            publicPath: '..',
            inject: false,
            minify: false,
        }),
        copyPlugin,
    ],
    stats: {
        loggingDebug: ['sass-loader'],
    /*    assetsSpace: 99,
        dependentModules: true,
        depth: true,
        entrypoints: true,
        moduleAssets: true,
        moduleTrace: true,
        providedExports: true,
        reasons: true,
        usedExports: true,
        assets: true,
        children: true,
        groupReasonsByOrigin: true,*/
    },
    entry: {
        bundle: ['./app/index.ts'],
        //     fonts: [ './app/fonts.js']
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
        ],
        hot: 'only',
        liveReload: false,
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
        extensions: ['.ts', '.mts', '.tsx', '.js', '.mjs', '.woff2'],
        symlinks: false,
        alias: {
            fonts: path.resolve(__dirname, 'fonts'),
            '../fonts': path.resolve(__dirname, 'fonts'),
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
        usedExports: false,
        sideEffects: false,
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
                test: /\.txt$/,
                type: 'asset/source',
                //use: [{ loader: 'raw-loader' }],
            },
            {
                test: /\.ne$/,
                use: ['nearley-loader'],
            },
            {
                test: path.resolve(__dirname, 'puffin', 'css', 'fonts.scss'),
                type: 'asset/inline',
                generator: { emit: false, binary: false, filename: 'foo.css' },
                use: [{ loader: MiniCssExtractPlugin.loader, options: {emit: false} }, 'css-loader'],
            },
            {
                test: /\.s[ac]ss$/i,
                resourceQuery: { not: [/raw/] },
                type: 'asset/resource',
                generator: {
                    filename: 'static/css/[name].css',
                    binary: false,
                },
                exclude: /node_modules/,
                use: [
                    // turns SCSS code into CSS
                    //MiniCssExtractPlugin.loader,'css-loader',
                    {
                        loader: 'sass-loader',
                        options: {
                            api: 'modern-compiler',
                            sassOptions: {
                                sourceMap: true,
                                style: 'expanded',
                                silenceDeprecations: ['import', 'legacy-js-api', 'color-functions'],
                            },
                        },
                    },
                ],
            },
            {
                test: /\.(eot|ttf|woff|woff2)$/i,
                type: 'asset/resource',
                generator: {
                    filename: 'static/fonts/[path][name][ext]',
                },
            },
            {
                test: /\.(png|jpg|gif|svg)$/i,
                type: 'asset/resource',
            },
        ],
    },
};

export default function init(env, argv) {
    config.mode = argv.mode || 'development';
    console.log('MODE: ', config.mode);
    if (config.mode === 'development') {
        config.devtool = 'source-map';
    } else if (config.mode === 'production') {
        config.output.path = path.resolve(__dirname, 'prod-dist', 'webroot');
        config.devtool = 'source-map';
        config.optimization.minimize = false;
        config.devServer = undefined;
    }
    return config;
}

//export default init;
