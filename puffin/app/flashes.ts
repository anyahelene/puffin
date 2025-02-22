import { Hole, html } from "uhtml";
let setTimeout = window.setTimeout;
const remove_flash_after = 3000;

const flash_log = document.querySelector('#flash-log');
let timer = -1;
function set_timer(handler: Function, timeout: number) {
    if (timer >= 0) {
        window.clearTimeout(timer);
    }
    timer = window.setTimeout(() => { timer = -1; handler() }, timeout);
}
function remove_flash(flash: HTMLElement) {
    if (!flash.classList.contains('remove')) {
        flash.style.setProperty('max-height', getComputedStyle(flash).height); //`${flash.clientHeight}px`);
        getComputedStyle(flash).height;
        flash.classList.add('remove');
    }
}
const close_all_after_timeout = () => {
    const flash = document.querySelector('#flashes :first-child') as HTMLElement;
    if (flash) {
        if (flash.classList.contains('remove')) {
            flash.remove();
        } else {
            remove_flash(flash);
        }
        set_timer(close_all_after_timeout, 3000);
    }
}
const transition_handler = (ev: TransitionEvent) => {
    const flash = ev.target as HTMLElement;
    if (flash.classList.contains('remove')) {
        setTimeout(() => {
            console.log(flash.scrollHeight, flash.clientHeight)
            if (flash_log) {
                flash.classList.remove('remove');
                flash.style.removeProperty('max-height');
                flash_log.appendChild(flash);
            } else {
                //  flash.remove();
            }
            // flash.remove();
        }, 100);
    }
}
const click_handler = (ev) => remove_flash(ev.currentTarget);
const flash_added = (flash: HTMLElement, i: number, parent: NodeListOf<Element> = undefined) => {
    flash.addEventListener('click', click_handler);
    flash.addEventListener('transitionend', transition_handler)
    set_timer(close_all_after_timeout, 3000);
}
export function activate_flashes() {
    document.querySelectorAll('.flash').forEach(flash_added);
}
export function show_flash(content: string | Record<string, any> | Hole, category = "message") {
    const flashes = document.querySelector('#flashes');
    if (!flashes)
        return;
    let s = content;
    console.log("show_flash", content);
    if (typeof content !== 'string' && !(content instanceof Hole)) {
        s = content.message;
        if (Array.isArray(content.args) && content.args.length > 0) {
            s = `${s}: ${content.args.map(a => `${a}`).join(', ')}`
        }
    }
    const node = html.node`<li class="flash"><div class="flash-inner">${s}</div></li>`;
    node.classList.add(category)
    flashes.appendChild(node);
    flash_added(node, 0);
}