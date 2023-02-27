import { BorbPanelBuilder } from '../borb/Frames';
import { html } from 'uhtml';
import { Group, tables, User } from './model';
export let csrf_token: string = undefined;

tables['with_member_list'] = [{ name: 'members', type: 'member[]' }];
tables['with_group_list'] = [{ name: 'groups', type: 'group[]' }];

export async function updateToken() {
    const res = await fetch('heartbeat', { method: 'GET' });
    console.log(res);

    if (res.ok) {
        const result = await res.json();
        console.log(result);
        if (result.status === 'ok') {
            csrf_token = result.csrf_token;
            return csrf_token;
        }
    }

    throw new Error('Failed to obtain CSRF token');
}
export async function request(
    endPoint: string,
    method: string = 'GET',
    params: Record<string, object | boolean | number | string> = undefined,
    use_url_params = false
) {
    const has_token = !!csrf_token;
    const tok = csrf_token || (await updateToken());
    let url = endPoint;
    const req: RequestInit = {
        method,
        headers: { 'X-CSRFToken': tok, Accept: 'application/json' },
    };
    if (params) {
        if (method === 'GET' || method === 'HEAD' || use_url_params) {
            const usp = new URLSearchParams();
            for (const p in params) {
                if (params[p] !== undefined && params[p] !== false && params[p] !== null)
                    usp.set(p, JSON.stringify(params[p]));
            }
            const p = usp.toString();
            if (p) url = endPoint + '?' + p;
        } else {
            req.body = JSON.stringify(params);
            req.headers['Content-Type'] = 'application/json; charset=UTF-8';
        }
    }
    const res = await fetch(url, req);
    if (res.ok) {
        const result = await res.json();
        console.log('JSON result:', result);
        return result;
    } else {
        let result = '';
        try {
            result = await res.text();
        } catch (e) {
            // ignore
        }
        if (has_token && result.search(/The CSRF token has expired/) !== -1) {
            console.warn('Resetting CSRF token');
            csrf_token = undefined;
            return request(endPoint, method, params);
        }
        throw new Error(`${res.status} ${res.statusText} ${result}`);
    }
}

function element(text: string | number | HTMLElement = '', tag = 'div') {
    const elt = document.createElement(tag);
    if (typeof text === 'string' || typeof text === 'number') elt.innerText = `${text}`;
    else if (text) elt.appendChild(text);
    return elt;
}
interface ColumnSpec {
    name?: string;
    head?: string;
    type?: string;
    mapping?: (val: any) => any;
    doc?: string;
    hide?: boolean;
    icons?: Record<string, string>;
}

function getColumnInfo(col_or_name: ColumnSpec | string): ColumnSpec {
    let col: ColumnSpec;
    if (typeof col_or_name === 'string') {
        col = { name: col_or_name };
        if (!col.type && (col.name === 'id' || col.name.endsWith('_id'))) col.type = 'number';
    } else {
        col = col_or_name;
    }
    return col;
}
function keys(obj) {
    const keys = [];
    for (let key in obj) keys.push(key);
    return keys;
}
function handle_internal_link(ev: MouseEvent) {
    if (ev.target instanceof HTMLAnchorElement) {
        const display = document.getElementById('display');
        const target = ev.target.dataset.target;
        switch (ev.target.dataset.type) {
            case 'group':
                console.log(parseInt(target));
                /*const group = Course.groups[parseInt(target)];
                console.log(group, DATA);
                if (group && display) display.innerText = JSON.stringify(group);*/
                break;
        }
        ev.preventDefault();
    }
}
export function display_panel(title: string) {
    return new BorbPanelBuilder()
        .frame('frame2')
        .panel('div', 'display_panel')
        .title(title)
        .select()
        .done();
}
function display_group(group: Group | Group[]): HTMLElement {
    if (!Array.isArray(group)) group = [group];
    const result = [];
    group.forEach((g) => {
        console.log(g);
        if (result.length > 0) result.push(html`, `);
        if (typeof g.id === 'number') {
            const link = `group?id=${g.id}`;
            result.push(
                html`<a
                    href=${link}
                    data-target=${g.id}
                    data-type="group"
                    onclick=${handle_internal_link}
                    >${g.slug || ''}</a
                >`,
            );
        }
    });

    return html.node`${result}`;
}

function display_obj(obj: any | any[], type: string): HTMLElement {
    if (!Array.isArray(obj)) obj = [obj];
    const result = [];
    let comma = '';
    obj.forEach((g) => {
        if (result.length > 0) comma = ', ';
        if (typeof g.id === 'number') {
            const link = `${type}?id=${g.id}`;
            result.push(
                html`${comma}<a
                        href=${link}
                        data-target=${g.id}
                        data-type="group"
                        onclick=${handle_internal_link}
                        >${g.slug || ''}</a
                    >`,
            );
        }
    });

    return html.node`${result}`;
}
export function to_table(tdata: any[] | any, cols: (ColumnSpec | string)[] = undefined) {
    let type: string;
    if (!Array.isArray(tdata)) {
        if (tdata._type?.endsWith('[]')) {
            type = tdata._type.slice(0, -2);
            const table_data = tdata[`{tdata._type}s`] || tdata.data;
            if (Array.isArray(table_data)) tdata = table_data;
            else tdata = [tdata];
        } else tdata = [tdata];
    }
    type = type || tdata[0]?._type || 'any';
    const more_types = type.split(',').slice(1);
    type = type.split(',')[0];
    let currentRow = element(null, 'tr');
    const thead = element(currentRow, 'thead'),
        tbody = element(null, 'tbody');
    const nextRow = () => {
        currentRow = element(null, 'tr');
        tbody.appendChild(currentRow);
    };
    const result: HTMLElement[] = [thead, tbody];
    const cell = (text: string | number | HTMLElement, tag = 'td') => {
        const elt = element(text, tag);
        currentRow.appendChild(elt);

        return elt;
    };
    cols = cols || tables[type] || keys(tdata[0]);
    more_types.forEach((t) => {
        if (tables[type]) cols = cols.concat(tables[t]);
    });
    const columns = cols.map((c) => getColumnInfo(c)).filter((c) => !(c.type === 'meta' || c.hide));
    //console.log(type, more_types, columns);
    for (let col of columns) {
        const elt = cell(col.head || col.name, 'th');
        elt.title = col.name;
        elt.dataset.type = col.type || 'any';
    }
    currentRow.dataset.type = type;
    thead.appendChild(currentRow);

    currentRow = element(null, 'tr');
    tdata.forEach((row) => {
        //console.log(row);
        nextRow();
        for (let spec of columns) {
            const value = row[spec.name];
            let content = value;
            if (spec.icons) content = spec.icons[`${value}`] || spec.icons[''] || value;
            else if (spec.type === 'bool')
                content = typeof value === 'string' ? value : value ? '✅' : '❌';
            else if (value instanceof Date) content = value?.toLocaleDateString();
            else if (value === undefined || value === null) {
                content = '';
            }
            let elt: HTMLElement;
            switch (spec.type) {
                case 'img':
                    elt = cell(html.node`<img src="${value}">`);
                    break;
                case 'datetime':
                    elt = cell(value?.toLocaleDateString() || '');
                    break;
                case 'user[]':
                    elt = cell(value.map((u: User) => u.lastname).join(', '));
                    break;
                case 'member[]':
                    elt = cell(display_obj(value, 'user'));
                    break;
                case 'group[]':
                    elt = cell(display_group(value));
                    break;
                default:
                    if (typeof content === 'string' || typeof content == 'number') {
                        elt = cell(content);
                    } else {
                        elt = cell(JSON.stringify(content));
                    }
            }
            elt.dataset.type = spec.type || 'any';
            if (!elt.title && value != content) elt.title = `${value}`;
        }
    });
    const foot = element('', 'td') as HTMLTableCellElement;
    foot.colSpan = currentRow.childElementCount;
    result.push(element(element(foot, 'tr'), 'tfoot'));
    return result;
}
