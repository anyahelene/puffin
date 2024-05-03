import { html, render } from 'uhtml';
export const GITLAB_PREFIX = 'https://git.app.uib.no/';
export const GITLAB_PATH_RE = '([a-zA-Z0-9_\\.][a-zA-Z0-9_\\-\\.]*[a-zA-Z0-9_\\-]|[a-zA-Z0-9_])';
export const SLUG_RE = '[a-zA-Z0-9_+\\-]+';

export function form_field(data: Record<string, any>) {
    data.ref = data.ref || { current: undefined };
    data.field = data.field || data.name || data.id;
    data.name = data.name || data.field || data.id;
    data.id = data.id || `_form_${data.field}_`;
    const obj = data.obj;
    data.value = data.value || obj[data.field];
    const onchange = data.onchange;
    data.type = data.type || 'text';
    data.link = data.link || data.link_prefix ? `${data.link_prefix}${data.value}` : undefined;
    const changeHandler = (ev) => {
        if (onchange) onchange(ev, data.ref.current, obj, data);
        else if (data.ref.current && data.ref.current.checkValidity() && data.field && obj)
            obj[data.field] = data.ref.current.value;
    };
    const button2 = data.button2_title
        ? html`<button
              type="button"
              class=${data.button2_class}
              onclick=${data.button2_make_onclick(data)}
              >${data.button2_title}</button
          >`
        : '';
    const button = data.button_title
        ? html`<span class="buttons">
              <button
                  type="button"
                  class=${data.button_class}
                  onclick=${data.button_make_onclick(data)}
                  >${data.button_title}</button
              >${button2 || ''}</span
          >`
        : '';
    const label = data.label === false ? '' : html`<label for=${data.id}>${data.name}:</label>`;
    if (data.editable)
        return html`<div class="form-field">
            ${label}
            <input
                type=${data.type}
                id=${data.id}
                ref=${data.ref}
                name=${data.field}
                required=${data.required}
                placeholder=${data.placeholder || ''}
                pattern=${data.pattern}
                onchange=${changeHandler}
                value=${data.value || ''}
                ?disabled=${data.disabled}
                size=${data.size}
            />
            ${button}
        </div>`;
    else if (data.link && data.value)
        return html`<div class="form-field">
            ${label}
            <span class="field" id=${data.id}
                ><a href=${data.link} target="_blank">${data.value || '\u202f'}</a></span
            >
            ${button}
        </div>`;
    else
        return html`<div class="form-field">
            ${label}
            <span class="field" id=${data.id}>${data.value || '\u202f'}</span>
            ${button}
        </div> `;
}

export function form_select(data: Record<string, any>) {
    const ref = data.ref || { current: undefined };
    const field = data.field || data.id;
    const id = data.id || `_form_${data.field}_`;
    const obj = data.obj;
    const value = data.value || obj[field];
    const onchange = data.onchange;
    const type = data.type || 'text';
    const link = data.link || data.link_prefix ? `${data.link_prefix}${value}` : undefined;
    const changeHandler = (ev) => {
        if (onchange) onchange(ev, ref.current, obj, field);
        else if (ref.current && ref.current.checkValidity() && field && obj)
            obj[field] = ref.current.value;
    };
    const formatOption = (alt: any, i: number) => {
        let value: string, text: string;
        if (Array.isArray(alt)) {
            value = alt[0];
            text = alt[1]?.toString();
        } else {
            value = text = alt?.toString();
        }
        return html`<option .selected=${data.default === value} value="${value}">${text}</option>`;
    };
    if (data.editable)
        return html`<div class="form-field">
            <label for=${id}>${data.name}:</label>
            <select
                type=${type}
                id=${id}
                ref=${ref}
                name=${field}
                required=${data.required}
                onchange=${changeHandler}
            >
                ${data.alternatives.flatMap(formatOption)}
            </select>
            ${data.button_title
                ? html`<span class="buttons">
                      <button
                          type="button"
                          class=${data.button_class}
                          onclick=${data.button_make_onclick(ref, field)}
                          >${data.button_title}</button
                      ></span
                  >`
                : ''}
        </div>`;
    else if (link && value)
        return html`<div class="form-field">
            <label for=${data.id}>${data.name}:</label>
            <span class="field" id=${data.id}
                ><a href=${link} target="_blank">${value || '\u202f'}</a></span
            >
        </div>`;
    else
        return html`<div class="form-field">
            <label for=${data.id}>${data.name}:</label>
            <span class="field" id=${data.id}>${value || '\u202f'}</span>
        </div>`;
}
