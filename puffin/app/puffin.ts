import { html } from 'uhtml';
import { BorbPanelBuilder } from '../borb/Frames';
import { show_flash } from './flashes';
import { Course, Group, User, tables } from './model';
export let csrf_token: string = undefined;

export const puffin: Record<string, object> = {
    debug: { console: false }
};

export function modify_table(
    table: string | ColumnSpec[],
    entry_name: string,
    f: (entry: ColumnSpec) => void,
) {
    const _table = Array.isArray(table) ? table : (tables[table] as ColumnSpec[]);

    return _table.find((entry) => {
        if (entry.name === entry_name) {
            f(entry);
            return true;
        } else {
            return false;
        }
    });
}
//tables['with_member_list'] = [{ name: 'members', type: 'member[]' }];
//tables['with_group_list'] = [{ name: 'groups', type: 'group[]' }];
tables['FullUser'].push({ name: 'team', type: 'group[]', filter: '' });
tables['FullUser'].push({ name: 'section', type: 'group[]', filter: '' });
//tables['FullUser'].push({ name: 'groups', type: 'group[]', filter: '' });
modify_table('FullUser', 'canvas_username', (entry) => {
    entry.mapping = (field, obj, spec) =>
        field
            ? html.node`<a title=${obj.canvas_id
                } class="external" href="${`https://mitt.uib.no/courses/${Course.current.external_id}/users/${obj.canvas_id}`}" target="_blank">${field}</a>`
            : '';
    entry.type = 'custom';
});
modify_table('FullUser', 'gitlab_username', (entry) => {
    entry.mapping = (field, obj, spec) =>
        field
            ? html.node`<a title=${obj.gitlab_id
                } class="external" href="${`https://git.app.uib.no/${obj.gitlab_username}/`}" target="_blank">${field}</a>`
            : '';
    entry.type = 'custom';
});
modify_table('FullUser', 'canvas_id', (entry) => (entry.hide = true));
modify_table('FullUser', 'gitlab_id', (entry) => (entry.hide = true));

//tables['Group'].push({ name: 'parent_id', type: 'group' });

class RequestError extends Error {
    _orig_response: Response;
    data: Record<string, any>;
    userMessage: string;

    constructor(res: Response, content: string, data: Record<string, any> = undefined) {
        if (!data) {
            try {
                data = JSON.parse(content);
            } catch {
                data = { message: content };
            }
        }
        super(`${res.status} ${res.statusText} ${content}`);
        if (data.message) {
            this.userMessage = data.message;
        } else {
            this.userMessage = this.message;
        }
        this.data = data;
    }
}
export async function updateToken() {
    const res = await fetch('heartbeat', {
        method: 'GET',
        headers: { Accept: 'application/json' },
    });
    //console.log(res);

    if (res.ok) {
        console.log('updateToken: ', res.status, res.statusText);
        const result = await res.json();
        //console.log(result);
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
    use_url_params = false,
    allow_error = false,
): Promise<any> {
    const has_token = !!csrf_token;
    const tok = csrf_token || (await updateToken());
    let url = new URL(endPoint, document.URL);
    const req: RequestInit = {
        method,
        headers: { 'X-CSRFToken': tok, Accept: 'application/json' },
    };
    const get_result = async (res: Response) => {
        const blob = await res.blob();

        if(blob.type === 'application/json') {
            return JSON.parse(await blob.text());
        } else {
            const result = { status: res.ok ? 'ok' : 'error', data:await blob.text(), status_code:res.status}
            console.error('hmm... should this be JSON, maybe?', result)
            return result;
        }

    }
    if (params) {
        if (method === 'GET' || method === 'HEAD' || use_url_params) {
            const usp = new URLSearchParams();
            for (const p in params) {
                if (params[p] !== undefined && params[p] !== false && params[p] !== null)
                    usp.set(p, JSON.stringify(params[p]));
            }
            const p = usp.toString();
            if (p) url.search = p;
        } else {
            req.body = JSON.stringify(params);
            req.headers['Content-Type'] = 'application/json; charset=UTF-8';
        }
    }
    const res = await fetch(url, req);
    let result: Record<string, any> = await get_result(res);
    console.log('fetch', url.toString(), req, '\n', res, '\n', result);

    log_request(res, JSON.stringify(result, null, 2));
    if (result.status === 'error') {
        if (has_token && result.message.search(/The CSRF token has expired/) !== -1) {
            console.warn('Resetting CSRF token');
            csrf_token = undefined;
            return request(endPoint, method, params);
        }
        else if (result.login_required && result.login_url) {
            // TODO: use popup window
            window.location.replace(result.login_url);
        }
        else if (!allow_error) {
            show_flash(result.message, "error");
            console.error('Request failed', result, '\nrequest:', req, '\nresponse:', res);
            throw new RequestError(res, result.message || 'Unknown error', result);
        }
    }
    return result;
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
    mapping?: (val: any, obj: Record<string, any>, spec: ColumnSpec) => HTMLElement | string; // TODO
    doc?: string;
    hide?: boolean;
    icons?: Record<string, string>;
    filter?: string;
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
export function user_emails(users: User[]) {
    return users.map(u => `${u.firstname} ${u.lastname} <${u.email}>`).join(', ');
}

export function handle_internal_link(ev: MouseEvent) {
    if (ev.target instanceof HTMLAnchorElement || ev.target instanceof HTMLButtonElement) {
        ev.preventDefault();
        const target = ev.target.dataset.target;
        switch (ev.target.dataset.type) {
            case 'group':
                console.log('handle_internal_link', target, parseInt(target), ev.target);
                const group: Group = Course.current.groupsById[parseInt(target)];
                group.display();
                break;
        }
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

export function login_panel(url: string) {
    const panel = new BorbPanelBuilder()
        .frame('frame2')
        .panel('div', 'login_panel')
        .title('Login')
        .select()
        .done();
    return panel;
}
function display_obj(
    field_in: any | any[],
    type: string,
    obj: Record<string, any>,
    spec?: ColumnSpec,
): HTMLElement {
    const field = Array.isArray(field_in) ? field_in : [field_in];
    const result = [];
    let comma = '';
    field.forEach((g) => {
        if (spec && spec.filter && g.kind !== spec.filter) return;
        if (result.length > 0) comma = ', ';
        if (typeof g.as_link === 'function') {
            result.push(g.as_link())
        }
    });

    return html.node`${result}`;
}

const hide_columns = [
    'course_id',
    'course_canvas_id',
    'course_name',
    'course_slug',
    'discord_id',
    'discord_username',
];
export function to_table(
    tdata_in: Record<string, any>[] | Record<string, any>,
    cols: (ColumnSpec | string)[] = undefined,
    selectable = true,
) {
    let type: string;
    let tdata: Record<string, any>[];
    if (Array.isArray(tdata_in)) {
        tdata = tdata_in;
    } else {
        if (tdata_in._type?.endsWith('[]')) {
            type = tdata_in._type.slice(0, -2);
            const table_data = tdata_in[`{tdata._type}s`] || tdata_in.data;
            if (tdata_in.selectable !== undefined) selectable = tdata_in.selectable;
            if (Array.isArray(table_data)) tdata = table_data;
            else tdata = [tdata_in];
        } else tdata = [tdata_in];
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
    const columns = cols
        .map((c) => getColumnInfo(c))
        .filter(
            (c) =>
                !(
                    c.type === 'meta' ||
                    c.hide ||
                    c.name.startsWith('_') ||
                    hide_columns.includes(c.name)
                ),
        );
    //console.log(type, more_types, columns);
    let allbox: HTMLInputElement = null;
    const checkboxes: HTMLInputElement[] = [];
    const selected: Set<HTMLInputElement> = new Set();
    const select = (ev: Event) => {
        const checked = checkboxes.filter((b) => b.checked);
        console.log('select', checked.length, checkboxes.length, ev);
        if (checked.length === 0) allbox.checked = false;
        else if (checked.length === checkboxes.length) allbox.checked = true;
        else {
            allbox.indeterminate = true;
            allbox.checked = false;
        }
        allbox.title = `${checked.length} of ${checkboxes.length} selected`;
    };
    if (puffin.debug['console']) {
        const elt = cell('', 'th')
        elt.classList.add('center', 'no-sort');
    }
    if (selectable) {
        allbox = document.createElement('input');
        allbox.type = 'checkbox';
        allbox.name = '__all__';
        allbox.addEventListener('change', (ev) => {
            checkboxes.forEach((b) => (b.checked = allbox.checked));
            allbox.title = `${allbox.checked ? checkboxes.length : 0} of ${checkboxes.length
                } selected`;
        });
        const elt = cell(allbox, 'th');
        elt.classList.add('center', 'no-sort');
        elt.dataset.type = 'bool';
    }
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
        currentRow.dataset.id = `${row.id}`;
        if (puffin.debug['console']) {
            const debug = () => console.log(row);
            const button = html.node`<button class="center no-sort" type="button" onclick=${debug}>🖨️</button>`
            cell(button, 'td')
        }
        if (selectable) {
            const box = document.createElement('input');
            box.type = 'checkbox';
            box.name = `${row.id}`;
            box.addEventListener('input', select);
            box.addEventListener('click', (ev) => console.log(ev));
            checkboxes.push(box);
            const elt = cell(box, 'td');
            elt.classList.add('center', 'no-sort');
            elt.dataset.type = 'bool';
        }
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
                case 'custom':
                    elt = cell(spec.mapping(value, row, spec));
                    break;
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
                    elt = cell(display_obj(value, 'user', row, spec));
                    break;
                case 'group.slug':
                    elt = cell(display_obj(row, 'group', row, spec));
                    break;
                case 'group[]':
                    elt = cell(display_obj(value, 'group', row, spec));
                    //console.log('group[] display', value, spec, elt);
                    break;
                default:
                    if (typeof content === 'string' || typeof content == 'number') {
                        elt = cell(content);
                    } else {
                        elt = cell(JSON.stringify(content));
                    }
            }
            elt.dataset.type = spec.type || 'any';
            if (!elt.title && value != content && value) elt.title = `${value}`;
        }
    });
    const foot = element(`${tdata.length}`, 'td') as HTMLTableCellElement;
    foot.colSpan = currentRow.childElementCount;
    result.push(element(element(foot, 'tr'), 'tfoot'));
    return result;
}

export async function get_gitlab_project(
    course: Course | number,
    project_ref: string,
): Promise<Record<string, any>> {
    if (project_ref) {
        if (typeof project_ref === 'string' && project_ref.startsWith('http'))
            project_ref = new URL(project_ref).pathname;
        const course_id = course instanceof Course ? course.external_id : course;
        //const proj = course_id
        //    ? await request(`courses/${course_id}/gitlab/${project_ref}`)
        //    : await request(`projects/gitlab/${project_ref}`);
        return await request(`projects/gitlab/${project_ref}`);
    }
}
export async function get_gitlab_group(
    course: Course | number,
    group_ref: string,
): Promise<Record<string, any>> {
    if (group_ref) {
        if (typeof group_ref === 'string' && group_ref.startsWith('http'))
            group_ref = new URL(group_ref).pathname;
        const course_id = course instanceof Course ? course.external_id : course;
        //const proj = course_id
        //    ? await request(`courses/${course_id}/gitlab_group/${group_ref}`)
        //    : await request(`projects/gitlab_group/${group_ref}`);
        return await request(`projects/gitlab_group/${group_ref}`);
    }
}
export async function create_team_from_project_url(
    course: Course,
    project_ref: string,
): Promise<Record<string, any>> {
    const project = await get_gitlab_project(undefined, project_ref);
    const name = project.namespace ? project.namespace.name : project.name;
    const slug = project.namespace ? project.namespace.path : project.path;
    const obj = {
        name,
        kind: 'team',
        join_model: 'AUTO',
        join_source: `gitlab(${project.id})`,
        slug,
    };
    const group = await request(`/courses/${course.external_id}/groups/`, 'POST', obj);
    console.log('create team', group);
    const sync_res = await request(
        `/courses/${course.external_id}/groups/${group.id}/sync`,
        'POST',
    );
    console.log('sync_result', sync_res);
    console.log('update group list', await course.updateGroups());
    console.log('update member lists', await course.updateMemberships());
    return group;
}
let reqId = 0;
export function log_request(res: Response, result: string) {
    const log = document.getElementById('output');
    log.querySelectorAll('details').forEach((elt) => (elt.open = false));
    const id = reqId++;
    const logEntry = document.createElement('details');
    logEntry.open = true;
    const head = document.createElement('summary');
    head.textContent = `[${id}]  (${res.status} ${res.statusText}) ${res.url} → ${res.status} ${res.statusText}`;
    const body = document.createElement('pre');
    body.innerText = result;
    logEntry.appendChild(head);
    logEntry.appendChild(body);
    log.appendChild(logEntry);
    logEntry.scrollIntoView({ block: 'start', inline: 'nearest', behavior: 'smooth' });
}

export function busy_event_handler<E extends Event>(
    handler: (ev: E) => Promise<void>,
    then: () => void,
    logTo: { log: (lvl: string, msg?: string) => void } | undefined = undefined,
    moreElements: (HTMLElement | { current?: HTMLElement })[] = [],
) {
    return async (ev: E) => {
        const target = ev.target as HTMLElement;
        const disabled = target['disabled'];
        const elts = moreElements
            .map((elt) => (elt instanceof HTMLElement ? elt : elt.current))
            .filter((elt) => elt);
        console.log('moreElements', moreElements);
        const disableElts = moreElements.filter((e) => {
            console.log('disabledElts', e);
            return e['disabled'] === false;
        });
        try {
            target.classList.remove('error');
            target.classList.add('busy');
            if (disabled === false) target['disabled'] = true;
            elts.forEach((e) => e.classList.add('busy'));
            disableElts.forEach((e) => (e['disabled'] = true));
            await handler(ev);
        } catch (e) {
            console.error(e);
            target.classList.add('error');
            if (logTo) logTo.log('error', e.userMessage);
        } finally {
            disableElts.forEach((e) => (e['disabled'] = false));
            elts.forEach((e) => e.classList.remove('busy'));
            if (disabled === false) target['disabled'] = false;
            (target as HTMLElement).classList.remove('busy');
            if (then) then();
        }
    };
}

export function gitlab_url(path: string) {
    return `https://git.app.uib.no/${path}`;
}
