import { MDRender, SubSystem, Borb, Buttons, Frames, Settings, History, Terminals } from '../borb';
//import defaultConfig from './config.json';
const defaultConfig = {};

const puffin : Record<string,object> = {}
puffin.SubSystem = SubSystem;
puffin.Borb = Borb;
window['puffin'] = puffin
SubSystem.setup(puffin, {
    proxy: true,
    hotReload: !!import.meta.webpackHot,
    global: true,
});
SubSystem.waitFor(Settings).then((settings) => {
    console.warn('CONFIGS:', settings.configs);
    settings.configs[4] = defaultConfig;
});

let reqId = 0;
let csrf_token = null;
const resultElt = document.getElementById('resultElt');
const anchor = document.getElementById('anchor');
const idField = document.getElementById('id') as HTMLInputElement;
const dataField = document.getElementById('data') as HTMLInputElement;
const submitBtn = document.getElementById('submit');

async function updateToken() {
    const res = await fetch("heartbeat", {method: 'GET'});
    console.log(res);

    if(res.ok) {
        const result = await res.json();
        console.log(result);
        if(result.status === 'ok') {
            csrf_token = result.csrf_token;
            return csrf_token;
        }
    }

    throw new Error('Failed to obtain CSRF token');
}
async function submit(method) {
    const endpoint = idField.value;
    const requestBody = dataField.value;
    const tok = csrf_token || await updateToken();
    const req : RequestInit = {method, headers:{'X-CSRFToken':tok, 'Accept':'application/json'}}
    if(method !== 'GET') {
        req.body = requestBody
        req.headers['Content-Type'] = 'application/json; charset=UTF-8'
    }
    const res = await fetch(endpoint, req);

    if (res.ok) {
        const result = await res.json();
        console.log("JSON result:", result);
        display_results(result);
    } else {
    }
};

function element(text : string | number | HTMLElement = '', tag = 'div') {
    const elt = document.createElement(tag);
    if (typeof text === 'string' || typeof text === 'number')
        elt.innerText = `${text}`;
    else if (text)
        elt.appendChild(text);
    return elt;
}
function display_results(result: any[]) {
    if(!Array.isArray(result) || result.length === 0) {
        resultElt.textContent = JSON.stringify(result, null, 2);
        return;
    }
    let currentRow = element(null, 'tr');
    const thead = element(currentRow, 'thead'), tbody = element(null, 'tbody');
    const nextRow = () => { currentRow = element(null, 'tr'); tbody.appendChild(currentRow); };
    resultElt.replaceChildren(thead, tbody);
    const cell = (text: string | number | HTMLElement, tag = 'td') => {
        const elt = element(text, tag);
        currentRow.appendChild(elt);

        return elt;
    };
    let columns = []
    for (let key in result[0]) {
        const elt = cell(`${key}`, 'th');
        elt.title = `${key}`;
        columns.push(key)
    }
    thead.appendChild(currentRow);

    currentRow = element(null, 'tr')
    result.forEach(row => {
        console.log(row)
        nextRow();
        for (let key of columns) {
            console.log(key, row[key])
            const elt = cell(`${JSON.stringify(row[key])}`);
        }
    });
    const foot = element("",'td') as HTMLTableCellElement
    foot.colSpan = currentRow.childElementCount
    resultElt.appendChild(element(element(foot, 'tr'), 'tfoot'));
    if(resultElt.getBoundingClientRect().y < 0)
        resultElt.scrollIntoView({ block: "start", inline: "nearest", behavior: "smooth" });
}

function enterPressed(ev:KeyboardEvent) {
    if (ev.key === 'Enter') {
        submit('GET');
    }
};
idField.addEventListener('keydown', enterPressed);
document.getElementById('get').addEventListener('click', e => submit('GET'));
document.getElementById('put').addEventListener('click', e => submit('PUT'));
document.getElementById('post').addEventListener('click', e => submit('POST'));
document.getElementById('patch').addEventListener('click', e => submit('PATCH'));

//import '../css/style.scss';
import '../css/frames.scss';
import '../css/buttons.scss';
import '../css/common.scss';
import '../css/markdown.scss';
import '../css/terminal.scss';
import '../css/editor.scss';
//import styles from '../css/common.scss';
//console.log(styles)

if (import.meta.webpackHot) {
    console.warn('WebpackHot enabled');
    //turtleduck.webpackHot = import.meta.webpackHot;
    import.meta.webpackHot.accept(
        [
            '../css/style.scss',
            '../css/frames.scss',
            '../css/buttons.scss',
            '../css/common.scss',
            '../css/markdown.scss',
            '../css/terminal.scss',
            '../css/grid-display.scss',
            '../css/editor.scss',
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

