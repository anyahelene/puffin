import {
    MDRender,
    SubSystem,
    Borb,
    Buttons,
    Frames,
    Settings,
    Sheet,
    History,
    Terminals,
} from '../borb';
import { BorbPanelBuilder } from '../borb/Frames';

import { TilingWM, TilingWindow } from '../borb/TilingWM';
import { html } from 'uhtml';
//import defaultConfig from './config.json';
const defaultConfig = {};
import { csrf_token, display_panel, request, to_table, updateToken } from './puffin';
import { add_course, Courses, display_course, set_active_course, set_course_view } from './courses';

const puffin: Record<string, object> = {};
puffin.SubSystem = SubSystem;
puffin.Borb = Borb;
window['puffin'] = puffin;
SubSystem.setup(puffin, {
    proxy: true,
    hotReload: !!import.meta.webpackHot,
    global: true,
});
SubSystem.waitFor(Settings).then((settings) => {
    console.warn('CONFIGS:', settings.configs);
    settings.configs[4] = defaultConfig;
});

const layoutPrefs = {
    frame1: {
        width: 12,
        height: 6,
        iconified: false,
        maximized: false,
    },
    frame2: {
        width: 20,
        height: 6,
        iconified: false,
        maximized: false,
    },
    frame3: {
        width: 32,
        height: 10,
        iconified: false,
        maximized: false,
    },
};
const layoutSpec = {
    dir: 'H',
    items: [
        {
            size: 29,
            dir: 'V',
            max_container: true,
            items: [
                {
                    size: 9,
                    dir: 'H',
                    items: [
                        {
                            size: 15,
                            item: 'frame1',
                        },
                        {
                            size: 14,
                            item: 'frame2',
                        },
                    ],
                },
                {
                    size: 7,
                    item: 'frame3',
                },
            ],
        },
    ],
};
interface TilingWM {
    initialize: (spec: object, prefs: object) => void;
}
puffin.TilingWM = TilingWM;
puffin.TilingWindow = TilingWindow;
console.log('Hello!!');
const wm = new TilingWM('mid', 32, 16);
puffin.wm = wm;
window.addEventListener('DOMContentLoaded', (ev) => {
    wm.initialize(layoutSpec, layoutPrefs);
});
puffin.add_course = add_course;
puffin.courses = Courses;
puffin.set_active_course = set_active_course;
puffin.to_table = to_table;
puffin.set_course_view = set_course_view;
//SubSystem.waitFor(Frames.Frames).then((frames) => {
puffin.display_panel = display_panel;
//});
puffin.display_course = display_course;
console.log(display_course);
let reqId = 0;
const resultElt = document.getElementById('resultElt');
const anchor = document.getElementById('anchor');
const idField = document.getElementById('id') as HTMLInputElement;
const dataField = document.getElementById('data') as HTMLInputElement;
const submitBtn = document.getElementById('submit');

async function submit(method: string) {
    const endpoint = idField.value;
    const requestBody = dataField.value ? JSON.parse(dataField.value) : undefined;
    resultElt.replaceChildren(...to_table(await request(endpoint, method, requestBody)));
}

interface Group {
    group_id: number;
    group_slug: string;
}

const DATA = {
    groups: [] as Group[],
};

function enterPressed(ev: KeyboardEvent) {
    if (ev.key === 'Enter') {
        submit('GET');
    }
}
idField.addEventListener('keydown', enterPressed);
document.getElementById('get').addEventListener('click', (e) => submit('GET'));
document.getElementById('put').addEventListener('click', (e) => submit('PUT'));
document.getElementById('post').addEventListener('click', (e) => submit('POST'));
document.getElementById('patch').addEventListener('click', (e) => submit('PATCH'));

import '../borb/css/frames.scss';
import '../borb/css/buttons.scss';
import '../borb/css/common.scss';
import '../borb/css/markdown.scss';
import '../borb/css/terminal.scss';
import '../borb/css/editor.scss';
import '../borb/css/sheet.scss';
import '../css/style.scss';
//import styles from '../css/common.scss';
//console.log(styles)

if (import.meta.webpackHot) {
    console.warn('WebpackHot enabled');
    //turtleduck.webpackHot = import.meta.webpackHot;
    import.meta.webpackHot.accept(
        [
            '../borb/css/frames.scss',
            '../borb/css/buttons.scss',
            '../borb/css/common.scss',
            '../borb/css/markdown.scss',
            '../borb/css/terminal.scss',
            '../borb/css/editor.scss',
        ],
        function (outdated) {
            outdated.forEach((dep) => {
                console.log(dep);
                //turtleduck.styles.update(dep.replace('./', '').replace('.scss', '.css'));
            });
        },
        (err, context) => {
            console.error('HMR failed:', err, context);
        },
    );

    //  import.meta.webpackHot.accept('./css/frames.scss?raw', function (...args) {
    //		console.warn("frames", args);
    //	});
}
