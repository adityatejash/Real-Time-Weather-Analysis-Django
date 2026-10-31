/* ==========================================================================
   WeatherLab UI
   1. Animated weather icons (replaces OpenWeatherMap <img> icons)
   2. Weather effects (rain, sun, snow, thunder, mist, clouds, stars)
   3. Real city photos (famous landmark via Wikipedia, cached)
   4. Count-up numbers, live "updated" time
   ========================================================================== */
(function () {
    "use strict";

    var reduceMotion = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
    function rand(a, b) { return a + Math.random() * (b - a); }

    /* ---------------------------------------------------------------------
       1. Condition parsing  (OpenWeatherMap icon code + description)
       --------------------------------------------------------------------- */
    function parseCondition(code, desc, wind) {
        code = String(code || "");
        desc = String(desc || "").toLowerCase();
        var group = code.slice(0, 2);
        var night = code.slice(-1) === "n";
        var type = "clouds";

        switch (group) {
            case "01": type = "clear"; break;
            case "02": type = "partly"; break;
            case "03":
            case "04": type = "clouds"; break;
            case "09": type = "drizzle"; break;
            case "10": type = "rain"; break;
            case "11": type = "thunder"; break;
            case "13": type = "snow"; break;
            case "50": type = "mist"; break;
            default:
                if (/thunder|storm/.test(desc)) type = "thunder";
                else if (/snow|sleet|blizzard/.test(desc)) type = "snow";
                else if (/drizzle/.test(desc)) type = "drizzle";
                else if (/rain|shower/.test(desc)) type = "rain";
                else if (/mist|fog|haze|smoke|dust|sand|ash/.test(desc)) type = "mist";
                else if (/few clouds|scattered/.test(desc)) type = "partly";
                else if (/clear|sunny/.test(desc)) type = "clear";
        }

        var intensity = 1;
        if (/heavy|extreme|violent|torrential/.test(desc)) intensity = 1.6;
        else if (/light|drizzle|few/.test(desc)) intensity = 0.65;

        return {
            type: type,
            night: night,
            intensity: intensity,
            wind: clamp(parseFloat(wind) || 0, 0, 60)
        };
    }

    /* ---------------------------------------------------------------------
       2. Animated weather icons (flat, colourful)
       --------------------------------------------------------------------- */
    var CLOUD_PATH = "M20 50a11 11 0 0 1-1.2-21.9A15 15 0 0 1 47.6 25 12.5 12.5 0 0 1 48 50z";

    function sunSVG(cx, cy, r) {
        var rays = "";
        for (var i = 0; i < 8; i++) {
            var a = (i * Math.PI) / 4;
            var x1 = cx + Math.cos(a) * (r + 4), y1 = cy + Math.sin(a) * (r + 4);
            var x2 = cx + Math.cos(a) * (r + 9), y2 = cy + Math.sin(a) * (r + 9);
            rays += '<line x1="' + x1.toFixed(1) + '" y1="' + y1.toFixed(1) + '" x2="' + x2.toFixed(1) + '" y2="' + y2.toFixed(1) + '"/>';
        }
        return '<g class="wi-rays" style="transform-origin:' + cx + 'px ' + cy + 'px" stroke="#ffb703" stroke-width="3" stroke-linecap="round">' + rays + "</g>" +
            '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="#ffc933"/>';
    }
    function moonSVG(scale, tx, ty) {
        return '<g transform="translate(' + tx + " " + ty + ") scale(" + scale + ')">' +
            '<path d="M38 8a24 24 0 1 0 18 40A19 19 0 0 1 38 8z" fill="#ffe28a"/>' +
            '<circle cx="52" cy="14" r="1.6" fill="#fff6c9" class="wi-star"/><circle cx="58" cy="26" r="1.2" fill="#fff6c9" class="wi-star s2"/></g>';
    }
    function cloud(fill, transform, cls) {
        return '<g transform="' + (transform || "") + '"><path class="wi-cloud ' + (cls || "") + '" d="' + CLOUD_PATH + '" fill="' + fill + '"/></g>';
    }
    function drops(color) {
        var c = color || "#3aa0ff";
        return '<g stroke="' + c + '" stroke-width="3" stroke-linecap="round">' +
            '<path class="wi-drop d1" d="M24 53l-2.5 6"/><path class="wi-drop d2" d="M33 53l-2.5 6"/><path class="wi-drop d3" d="M42 53l-2.5 6"/></g>';
    }

    function iconSVG(code) {
        code = String(code || "03d");
        var g = code.slice(0, 2), night = code.slice(-1) === "n";
        var inner = "";
        switch (g) {
            case "01": inner = night ? moonSVG(1, 0, 0) : sunSVG(32, 32, 11); break;
            case "02":
                inner = (night ? moonSVG(0.62, 22, -2) : sunSVG(42, 22, 8)) + cloud("#f4f8ff", "translate(-6 7) scale(.92)"); break;
            case "03": inner = cloud("#dbe7f6", "translate(8 -6) scale(.7)") + cloud("#f4f8ff", "translate(-4 4)"); break;
            case "04": inner = cloud("#9fb1c9", "translate(10 -8) scale(.72)") + cloud("#dfe8f4", "translate(-4 4)"); break;
            case "09": inner = cloud("#cfdcee", "translate(0 -4)") + drops(); break;
            case "10": inner = (night ? "" : sunSVG(44, 18, 7)) + cloud("#e4edf8", "translate(-2 -3)") + drops(); break;
            case "11": inner = cloud("#a9b8cd", "translate(0 -6)") + '<path class="wi-bolt" d="M35 40l-9 13h6l-3 10 12-15h-7l4-8z" fill="#ffd43b"/>'; break;
            case "13": inner = cloud("#e9f1fb", "translate(0 -6)") +
                '<g fill="#fff"><circle class="wi-drop d1" cx="24" cy="54" r="2.4"/><circle class="wi-drop d2" cx="33" cy="57" r="2.4"/><circle class="wi-drop d3" cx="42" cy="54" r="2.4"/></g>'; break;
            case "50": inner = cloud("#c9d6e6", "translate(0 -8) scale(.95)") +
                '<g stroke="#b7c7dc" stroke-width="3" stroke-linecap="round"><path class="wi-mist m1" d="M16 48h30"/><path class="wi-mist m2" d="M22 55h30"/><path class="wi-mist m3" d="M14 62h26"/></g>'; break;
            default: inner = cloud("#f4f8ff", "translate(-2 2)");
        }
        return '<svg class="wi" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">' + inner + "</svg>";
    }

    function swapIcons() {
        var imgs = document.querySelectorAll('img[src*="openweathermap.org/img/wn/"]');
        Array.prototype.forEach.call(imgs, function (img) {
            var m = /wn\/([0-9]{2}[dn])/.exec(img.getAttribute("src") || "");
            if (!m) return;
            var holder = document.createElement("span");
            holder.innerHTML = iconSVG(m[1]);
            var svg = holder.firstChild;
            svg.setAttribute("class", "wi " + (img.className || ""));
            svg.setAttribute("width", img.getAttribute("width") || "56");
            svg.setAttribute("height", img.getAttribute("height") || "56");
            svg.setAttribute("role", "img");
            svg.removeAttribute("aria-hidden");
            svg.setAttribute("aria-label", img.getAttribute("alt") || "Weather");
            img.parentNode.replaceChild(svg, img);
        });
    }

    /* ---------------------------------------------------------------------
       3. Weather effects engine (canvas)
       --------------------------------------------------------------------- */
    function FX(canvas, cond, opts) {
        opts = opts || {};
        this.canvas = canvas;
        this.ctx = canvas.getContext("2d");
        this.cond = cond;
        this.ambient = !!opts.ambient;       // subtle full-page layer
        this.t = 0;
        this.running = false;
        this.inView = true;
        this.flash = 0;
        this.bolt = null;
        this.nextBolt = rand(1.5, 4);
        this.w = 0; this.h = 0;
        var self = this;
        this.resize();
        if (window.ResizeObserver && canvas.parentElement && !this.ambient) {
            new ResizeObserver(function () { self.resize(); }).observe(canvas.parentElement);
        } else {
            window.addEventListener("resize", function () { self.resize(); });
        }
    }

    FX.prototype.resize = function () {
        var dpr = Math.min(window.devicePixelRatio || 1, 2);
        var w = this.canvas.clientWidth, h = this.canvas.clientHeight;
        if (!w || !h) return;
        this.w = w; this.h = h;
        this.canvas.width = Math.round(w * dpr);
        this.canvas.height = Math.round(h * dpr);
        this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        this.build();
        if (!this.running) this.draw();
    };

    FX.prototype.build = function () {
        var c = this.cond, w = this.w, h = this.h, area = w * h;
        var k = (this.ambient ? 0.55 : 1) * c.intensity;
        var t = c.type;
        this.drops = []; this.ripples = []; this.flakes = []; this.clouds = [];
        this.stars = []; this.motes = []; this.bands = []; this.shooting = null;
        this.slant = 0.12 + c.wind / 110;
        this.skyH = Math.min(h, 520);

        var i;
        if (t === "rain" || t === "drizzle" || t === "thunder") {
            var base = clamp(area / 5200, 50, 340);
            var n = Math.round(base * k * (t === "drizzle" ? 0.7 : t === "thunder" ? 1.35 : 1));
            for (i = 0; i < n; i++) this.drops.push(this.newDrop(true));
        }
        if (t === "snow") {
            var ns = Math.round(clamp(area / 8000, 40, 240) * k);
            for (i = 0; i < ns; i++) {
                this.flakes.push({
                    x: rand(0, w), y: rand(0, h), r: rand(1.1, 3.4), v: rand(22, 60),
                    ph: rand(0, 6.28), sw: rand(8, 26), a: rand(0.5, 1)
                });
            }
        }
        var cc = 0;
        if (t === "clouds") cc = this.ambient ? 4 : 7;
        else if (t === "partly") cc = this.ambient ? 2 : 4;
        else if (t === "rain" || t === "drizzle" || t === "thunder") cc = this.ambient ? 3 : 6;
        else if (t === "snow") cc = this.ambient ? 2 : 4;
        else if (t === "mist") cc = this.ambient ? 2 : 3;
        for (i = 0; i < cc; i++) {
            this.clouds.push({
                x: rand(-150, w + 150), y: rand(-10, this.skyH * (this.ambient ? 0.35 : 0.5)),
                s: rand(0.8, 1.8), v: rand(5, 16) * (1 + c.wind / 40), a: rand(0.55, 1)
            });
        }
        if (t === "mist") {
            var nb = this.ambient ? 4 : 7;
            for (i = 0; i < nb; i++) {
                this.bands.push({
                    x: rand(-100, w), y: rand(h * 0.25, h * 0.95), w: rand(w * 0.5, w * 1.1),
                    h: rand(40, 110), v: rand(6, 16), a: rand(0.07, 0.15)
                });
            }
        }
        if (c.night && (t === "clear" || t === "partly")) {
            var nst = Math.round(clamp(Math.min(area, w * 700) / 3200, 40, 220) * (this.ambient ? 0.6 : 1));
            for (i = 0; i < nst; i++) {
                this.stars.push({ x: rand(0, w), y: rand(0, this.skyH * (this.ambient ? 0.9 : 1.1)), r: rand(0.4, 1.6), ph: rand(0, 6.28), sp: rand(0.8, 2.4) });
            }
        }
        if (!c.night && (t === "clear" || t === "partly")) {
            var nm = Math.round(clamp(Math.min(area, w * 700) / 16000, 8, 34) * (this.ambient ? 0.5 : 1));
            for (i = 0; i < nm; i++) {
                this.motes.push({ x: rand(0, w), y: rand(0, h), r: rand(0.8, 2.2), v: rand(6, 20), ph: rand(0, 6.28), a: rand(0.25, 0.7) });
            }
        }
    };

    FX.prototype.newDrop = function (anywhere) {
        var w = this.w, h = this.h;
        return {
            x: rand(-h * this.slant, w), y: anywhere ? rand(-h, h) : rand(-60, -10),
            l: rand(10, 24), v: rand(620, 1100), w: rand(0.7, 1.5), a: rand(0.22, 0.6),
            gy: h - rand(2, h * 0.12)
        };
    };

    /* --- drawing helpers --- */
    FX.prototype.drawCloud = function (cl) {
        var ctx = this.ctx, c = this.cond;
        var R = 38 * cl.s * clamp(this.w / 650, 0.65, 1.7);
        var dark = c.type === "rain" || c.type === "drizzle" || c.type === "thunder";
        var col = c.night ? "150,168,205" : dark ? "118,134,160" : "255,255,255";
        var alpha = (c.night ? 0.2 : dark ? 0.34 : 0.26) * cl.a * (this.ambient ? 0.7 : 1);
        var blobs = [[-1.15, 0.25, 0.8], [-0.45, -0.3, 1.0], [0.5, -0.2, 0.92], [1.2, 0.25, 0.72], [0.05, 0.38, 1.0]];
        for (var i = 0; i < blobs.length; i++) {
            var b = blobs[i], x = cl.x + b[0] * R, y = cl.y + b[1] * R, r = R * b[2] * 1.25;
            var g = ctx.createRadialGradient(x, y, 0, x, y, r);
            g.addColorStop(0, "rgba(" + col + "," + alpha + ")");
            g.addColorStop(1, "rgba(" + col + ",0)");
            ctx.fillStyle = g;
            ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
        }
    };

    FX.prototype.drawSun = function () {
        var ctx = this.ctx, t = this.t;
        var cx = this.ambient ? this.w * 0.92 : this.w * 0.78;
        var cy = this.ambient ? 40 : Math.min(this.skyH * 0.26, 150);
        var R = clamp(Math.min(this.w, this.skyH) * 0.075, 18, 52);
        var pulse = 1 + Math.sin(t * 1.4) * 0.06;

        if (this.ambient) {
            var ag = ctx.createRadialGradient(cx, cy, 0, cx, cy, 420 * pulse);
            ag.addColorStop(0, "rgba(255,200,110,0.16)");
            ag.addColorStop(1, "rgba(255,200,110,0)");
            ctx.fillStyle = ag;
            ctx.fillRect(cx - 430, cy - 430, 860, 860);
            return;
        }

        var glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 6 * pulse);
        glow.addColorStop(0, "rgba(255,214,120,0.5)");
        glow.addColorStop(0.35, "rgba(255,190,90,0.16)");
        glow.addColorStop(1, "rgba(255,190,90,0)");
        ctx.fillStyle = glow;
        ctx.fillRect(cx - R * 7, cy - R * 7, R * 14, R * 14);

        var n = 16;
        for (var i = 0; i < n; i++) {
            var a = (i / n) * 6.2832 + t * 0.07;
            var len = R * (i % 2 ? 1.7 : 2.6) * (0.9 + 0.1 * Math.sin(t * 1.6 + i));
            var x1 = cx + Math.cos(a) * R * 1.2, y1 = cy + Math.sin(a) * R * 1.2;
            var x2 = cx + Math.cos(a) * (R * 1.2 + len), y2 = cy + Math.sin(a) * (R * 1.2 + len);
            var lg = ctx.createLinearGradient(x1, y1, x2, y2);
            lg.addColorStop(0, "rgba(255,226,140,0.34)");
            lg.addColorStop(1, "rgba(255,226,140,0)");
            ctx.strokeStyle = lg; ctx.lineWidth = i % 2 ? 1.6 : 2.6; ctx.lineCap = "round";
            ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
        }
        var disc = ctx.createRadialGradient(cx - R * 0.3, cy - R * 0.3, R * 0.1, cx, cy, R);
        disc.addColorStop(0, "rgba(255,250,214,1)");
        disc.addColorStop(1, "rgba(255,185,60,1)");
        ctx.fillStyle = disc;
        ctx.beginPath(); ctx.arc(cx, cy, R, 0, 6.2832); ctx.fill();
    };

    FX.prototype.drawMoon = function () {
        var ctx = this.ctx;
        if (this.ambient) return;
        var cx = this.w * 0.78;
        var cy = Math.min(this.skyH * 0.24, 140);
        var R = clamp(Math.min(this.w, this.skyH) * 0.065, 16, 44);
        var amb = 1;
        var glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 5);
        glow.addColorStop(0, "rgba(205,222,255," + 0.38 * amb + ")");
        glow.addColorStop(1, "rgba(205,222,255,0)");
        ctx.fillStyle = glow; ctx.fillRect(cx - R * 5, cy - R * 5, R * 10, R * 10);
        var disc = ctx.createRadialGradient(cx - R * 0.35, cy - R * 0.35, R * 0.1, cx, cy, R);
        disc.addColorStop(0, "rgba(255,253,240," + amb + ")");
        disc.addColorStop(1, "rgba(220,226,240," + amb + ")");
        ctx.fillStyle = disc; ctx.beginPath(); ctx.arc(cx, cy, R, 0, 6.2832); ctx.fill();
        ctx.fillStyle = "rgba(160,170,195," + 0.28 * amb + ")";
        [[-0.3, 0.2, 0.22], [0.25, -0.25, 0.16], [0.3, 0.35, 0.12]].forEach(function (cr) {
            ctx.beginPath(); ctx.arc(cx + cr[0] * R, cy + cr[1] * R, cr[2] * R, 0, 6.2832); ctx.fill();
        });
    };

    FX.prototype.makeBolt = function () {
        var x = rand(this.w * 0.15, this.w * 0.85), y = -10, pts = [[x, y]];
        var gy = this.h * rand(0.55, 0.85);
        while (y < gy) { y += rand(22, 44); x += rand(-32, 32); pts.push([x, y]); }
        var branch = [];
        var bi = Math.floor(pts.length * rand(0.3, 0.6));
        var bx = pts[bi][0], by = pts[bi][1];
        branch.push([bx, by]);
        for (var i = 0; i < 4; i++) { by += rand(18, 34); bx += rand(10, 36) * (Math.random() < 0.5 ? -1 : 1); branch.push([bx, by]); }
        return { pts: pts, branch: branch, life: 0.22 };
    };

    FX.prototype.step = function (dt) {
        var i, d, f, cl, b, s, m, w = this.w, h = this.h, t = this.cond.type;
        this.t += dt;

        for (i = 0; i < this.clouds.length; i++) {
            cl = this.clouds[i]; cl.x += cl.v * dt;
            if (cl.x - 260 > w) { cl.x = -260; cl.y = rand(-10, this.skyH * (this.ambient ? 0.35 : 0.5)); }
        }
        for (i = 0; i < this.drops.length; i++) {
            d = this.drops[i];
            d.x += d.v * this.slant * dt; d.y += d.v * dt;
            if (d.y >= d.gy) {
                if (!this.ambient && this.ripples.length < 40 && Math.random() < 0.45) {
                    this.ripples.push({ x: d.x, y: d.gy, r: 1, max: rand(8, 22), a: 0.5 });
                }
                this.drops[i] = this.newDrop(false);
            }
        }
        for (i = this.ripples.length - 1; i >= 0; i--) {
            var rp = this.ripples[i]; rp.r += dt * 38; rp.a = 0.5 * (1 - rp.r / rp.max);
            if (rp.r >= rp.max) this.ripples.splice(i, 1);
        }
        for (i = 0; i < this.flakes.length; i++) {
            f = this.flakes[i];
            f.y += f.v * dt; f.x += (Math.sin(this.t * 0.8 + f.ph) * f.sw + this.cond.wind * 0.8) * dt;
            if (f.y > h + 6) { f.y = -6; f.x = rand(0, w); }
            if (f.x > w + 10) f.x = -10; else if (f.x < -10) f.x = w + 10;
        }
        for (i = 0; i < this.bands.length; i++) {
            b = this.bands[i]; b.x += b.v * dt; if (b.x - b.w > w) b.x = -b.w;
        }
        for (i = 0; i < this.motes.length; i++) {
            m = this.motes[i]; m.y -= m.v * dt; m.x += Math.sin(this.t + m.ph) * 8 * dt;
            if (m.y < -6) { m.y = h + 6; m.x = rand(0, w); }
        }
        if (this.stars.length && !this.shooting && Math.random() < dt * 0.12) {
            this.shooting = { x: rand(w * 0.2, w), y: rand(0, h * 0.35), life: 0.9 };
        }
        if (this.shooting) { this.shooting.x -= 520 * dt; this.shooting.y += 260 * dt; this.shooting.life -= dt; if (this.shooting.life <= 0) this.shooting = null; }

        if (t === "thunder") {
            this.nextBolt -= dt;
            if (this.nextBolt <= 0) {
                this.flash = 1; this.bolt = this.makeBolt();
                this.nextBolt = rand(2.5, 6.5);
                if (Math.random() < 0.5) this.echo = 0.14;
            }
            if (this.echo) { this.echo -= dt; if (this.echo <= 0) { this.flash = 0.8; this.echo = 0; } }
            if (this.bolt) { this.bolt.life -= dt; if (this.bolt.life <= 0) this.bolt = null; }
            this.flash = Math.max(0, this.flash - dt * 3.2);
        }
    };

    FX.prototype.draw = function () {
        var ctx = this.ctx, w = this.w, h = this.h, c = this.cond, t = c.type, i;
        ctx.clearRect(0, 0, w, h);

        // stars
        for (i = 0; i < this.stars.length; i++) {
            var st = this.stars[i];
            var a = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(this.t * st.sp + st.ph));
            ctx.fillStyle = "rgba(255,255,255," + a.toFixed(2) + ")";
            ctx.beginPath(); ctx.arc(st.x, st.y, st.r, 0, 6.2832); ctx.fill();
        }
        if (this.shooting) {
            var sh = this.shooting, sa = clamp(sh.life, 0, 1);
            var sg = ctx.createLinearGradient(sh.x, sh.y, sh.x + 90, sh.y - 45);
            sg.addColorStop(0, "rgba(255,255,255," + sa + ")"); sg.addColorStop(1, "rgba(255,255,255,0)");
            ctx.strokeStyle = sg; ctx.lineWidth = 1.6; ctx.lineCap = "round";
            ctx.beginPath(); ctx.moveTo(sh.x, sh.y); ctx.lineTo(sh.x + 90, sh.y - 45); ctx.stroke();
        }

        // sun / moon
        if (t === "clear" || t === "partly") { if (c.night) this.drawMoon(); else this.drawSun(); }

        // mist
        for (i = 0; i < this.bands.length; i++) {
            var bd = this.bands[i];
            ctx.save(); ctx.translate(bd.x + bd.w / 2, bd.y); ctx.scale(1, bd.h / bd.w);
            var bg = ctx.createRadialGradient(0, 0, 0, 0, 0, bd.w / 2);
            bg.addColorStop(0, "rgba(235,242,250," + bd.a * (this.ambient ? 0.7 : 1) + ")");
            bg.addColorStop(1, "rgba(235,242,250,0)");
            ctx.fillStyle = bg; ctx.beginPath(); ctx.arc(0, 0, bd.w / 2, 0, 6.2832); ctx.fill(); ctx.restore();
        }

        // clouds
        for (i = 0; i < this.clouds.length; i++) this.drawCloud(this.clouds[i]);

        // motes (warm floating dust in sunlight)
        for (i = 0; i < this.motes.length; i++) {
            var m = this.motes[i];
            var mg = ctx.createRadialGradient(m.x, m.y, 0, m.x, m.y, m.r * 3);
            mg.addColorStop(0, "rgba(255,230,160," + m.a * (this.ambient ? 0.18 : 0.45) + ")"); mg.addColorStop(1, "rgba(255,230,160,0)");
            ctx.fillStyle = mg; ctx.beginPath(); ctx.arc(m.x, m.y, m.r * 3, 0, 6.2832); ctx.fill();
        }

        // rain
        if (this.drops.length) {
            ctx.lineCap = "round";
            for (i = 0; i < this.drops.length; i++) {
                var d = this.drops[i];
                ctx.strokeStyle = "rgba(190,215,255," + d.a.toFixed(2) + ")"; ctx.lineWidth = d.w;
                ctx.beginPath(); ctx.moveTo(d.x, d.y); ctx.lineTo(d.x - this.slant * d.l, d.y - d.l); ctx.stroke();
            }
            ctx.lineWidth = 1;
            for (i = 0; i < this.ripples.length; i++) {
                var rp = this.ripples[i];
                ctx.strokeStyle = "rgba(200,225,255," + Math.max(rp.a, 0).toFixed(2) + ")";
                ctx.beginPath(); ctx.ellipse(rp.x, rp.y, rp.r * 1.8, rp.r * 0.6, 0, 0, 6.2832); ctx.stroke();
            }
        }

        // snow
        for (i = 0; i < this.flakes.length; i++) {
            var f = this.flakes[i];
            ctx.fillStyle = "rgba(255,255,255," + f.a.toFixed(2) + ")";
            ctx.beginPath(); ctx.arc(f.x, f.y, f.r, 0, 6.2832); ctx.fill();
        }

        // lightning
        if (this.bolt) {
            var bo = this.bolt;
            ctx.save();
            ctx.shadowColor = "#9fc3ff"; ctx.shadowBlur = 22;
            ctx.strokeStyle = "rgba(235,242,255,0.95)"; ctx.lineWidth = 2.4; ctx.lineJoin = "round";
            [bo.pts, bo.branch].forEach(function (p, idx) {
                ctx.lineWidth = idx ? 1.4 : 2.4;
                ctx.beginPath(); ctx.moveTo(p[0][0], p[0][1]);
                for (var j = 1; j < p.length; j++) ctx.lineTo(p[j][0], p[j][1]);
                ctx.stroke();
            });
            ctx.restore();
        }
        if (this.flash > 0.01) {
            ctx.fillStyle = "rgba(205,220,255," + (this.flash * (this.ambient ? 0.1 : 0.32)).toFixed(3) + ")";
            ctx.fillRect(0, 0, w, h);
        }
    };

    FX.prototype.loop = function (now) {
        if (!this.running) return;
        var self = this;
        var dt = this.last ? Math.min((now - this.last) / 1000, 0.05) : 0.016;
        this.last = now;
        if (this.inView && !document.hidden) { this.step(dt); this.draw(); }
        requestAnimationFrame(function (n) { self.loop(n); });
    };
    FX.prototype.start = function () {
        if (reduceMotion) { this.step(0.016); this.draw(); return; }
        if (this.running) return;
        this.running = true; this.last = 0;
        var self = this;
        requestAnimationFrame(function (n) { self.loop(n); });
    };

    function startFX(canvas, cond, opts) {
        if (!canvas || !canvas.getContext) return null;
        var fx = new FX(canvas, cond, opts);
        if ("IntersectionObserver" in window && !(opts && opts.ambient)) {
            new IntersectionObserver(function (e) { fx.inView = e[0].isIntersecting; }, { threshold: 0 }).observe(canvas);
        }
        fx.start();
        return fx;
    }

    /* ---------------------------------------------------------------------
       4. City photos (famous landmark → city article → search), cached
       --------------------------------------------------------------------- */
    var LANDMARKS = {
        "bhopal": ["Taj-ul-Masajid", "Upper Lake, Bhopal", "Bhopal"],
        "indore": ["Rajwada"], "ujjain": ["Mahakaleshwar Jyotirlinga"], "gwalior": ["Gwalior Fort"],
        "jabalpur": ["Dhuandhar Falls"],
        "delhi": ["India Gate", "Red Fort"], "new delhi": ["India Gate"],
        "mumbai": ["Gateway of India"], "kolkata": ["Howrah Bridge", "Victoria Memorial, Kolkata"],
        "chennai": ["Kapaleeshwarar Temple"], "bengaluru": ["Vidhana Soudha"], "bangalore": ["Vidhana Soudha"],
        "hyderabad": ["Charminar"], "ahmedabad": ["Sidi Saiyyed Mosque"], "pune": ["Shaniwar Wada"],
        "jaipur": ["Hawa Mahal"], "agra": ["Taj Mahal"], "varanasi": ["Ghats in Varanasi"],
        "amritsar": ["Golden Temple"], "lucknow": ["Rumi Darwaza"], "udaipur": ["City Palace, Udaipur"],
        "jodhpur": ["Mehrangarh"], "chandigarh": ["Capitol Complex, Chandigarh"], "patna": ["Golghar"],
        "thiruvananthapuram": ["Padmanabhaswamy Temple"], "mysore": ["Mysore Palace"], "mysuru": ["Mysore Palace"],
        "nagpur": ["Deekshabhoomi"], "guwahati": ["Kamakhya Temple"], "srinagar": ["Dal Lake"],
        "shimla": ["Christ Church, Shimla"], "kochi": ["Chinese fishing nets"],
        "london": ["Big Ben"], "paris": ["Eiffel Tower"], "new york": ["Statue of Liberty"],
        "new york city": ["Statue of Liberty"], "tokyo": ["Tokyo Tower"], "rome": ["Colosseum"],
        "berlin": ["Brandenburg Gate"], "madrid": ["Royal Palace of Madrid"], "barcelona": ["Sagrada Família"],
        "amsterdam": ["Canals of Amsterdam"], "vienna": ["Schönbrunn Palace"], "prague": ["Charles Bridge"],
        "moscow": ["Saint Basil's Cathedral"], "istanbul": ["Hagia Sophia"], "dubai": ["Burj Khalifa"],
        "singapore": ["Marina Bay Sands"], "kuala lumpur": ["Petronas Towers"], "bangkok": ["Wat Arun"],
        "sydney": ["Sydney Opera House"], "melbourne": ["Flinders Street railway station"],
        "san francisco": ["Golden Gate Bridge"], "los angeles": ["Hollywood Sign"], "chicago": ["Cloud Gate"],
        "las vegas": ["Las Vegas Strip"], "washington": ["Washington Monument"], "toronto": ["CN Tower"],
        "rio de janeiro": ["Christ the Redeemer (statue)"], "cairo": ["Giza pyramid complex"],
        "cape town": ["Table Mountain"], "beijing": ["Forbidden City"], "shanghai": ["Oriental Pearl Tower"],
        "hong kong": ["Victoria Harbour"], "seoul": ["Gyeongbokgung"], "kathmandu": ["Boudhanath"],
        "lahore": ["Badshahi Mosque"], "lisbon": ["Belém Tower"], "athens": ["Parthenon"],
        "venice": ["Grand Canal (Venice)"], "edinburgh": ["Edinburgh Castle"]
    };

    function normKey(s) {
        var x = String(s || "").trim().toLowerCase();
        try { x = x.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); } catch (e) { /* old browsers */ }
        return x;
    }
    function countryName(code) {
        code = String(code || "").trim();
        if (/^[A-Za-z]{2}$/.test(code)) {
            try { return new Intl.DisplayNames(["en"], { type: "region" }).of(code.toUpperCase()) || code; } catch (e) { return code; }
        }
        return code;
    }
    function cacheGet(k) {
        try {
            var v = JSON.parse(localStorage.getItem(k) || "null");
            if (v && Date.now() - v.t < 30 * 864e5) return v.u;
        } catch (e) { /* ignore */ }
        return undefined;
    }
    function cacheSet(k, u) { try { localStorage.setItem(k, JSON.stringify({ t: Date.now(), u: u })); } catch (e) { /* ignore */ } }

    function wikiApi(params) {
        var q = Object.keys(params).map(function (k) { return encodeURIComponent(k) + "=" + encodeURIComponent(params[k]); }).join("&");
        return fetch("https://en.wikipedia.org/w/api.php?format=json&origin=*&" + q).then(function (r) { return r.json(); });
    }
    function pickThumb(pages) {
        if (!pages) return null;
        var list = Object.keys(pages).map(function (k) { return pages[k]; })
            .sort(function (a, b) { return (a.index || 0) - (b.index || 0); });
        for (var i = 0; i < list.length; i++) {
            var th = list[i].thumbnail;
            if (!th || !th.width || !th.height) continue;
            if (th.width / th.height < 1.25) continue;                       // landscape only
            if (/(map|flag|seal|logo|coat_of_arms|locator|emblem|location|diagram)/i.test(th.source)) continue;
            return th.source;
        }
        return null;
    }
    function byTitle(title) {
        return wikiApi({ action: "query", prop: "pageimages", piprop: "thumbnail", pithumbsize: 1280, redirects: 1, titles: title })
            .then(function (d) { return d && d.query ? pickThumb(d.query.pages) : null; })
            .catch(function () { return null; });
    }
    function bySearch(q) {
        return wikiApi({ action: "query", generator: "search", gsrsearch: q, gsrlimit: 6, gsrnamespace: 0, prop: "pageimages", piprop: "thumbnail", pithumbsize: 1280 })
            .then(function (d) { return d && d.query ? pickThumb(d.query.pages) : null; })
            .catch(function () { return null; });
    }

    var photoPromises = {};
    function resolveCityPhoto(city, country) {
        var key = normKey(city);
        if (!key) return Promise.resolve(null);
        var ck = "wl:photo:v1:" + key;
        var cached = cacheGet(ck);
        if (cached !== undefined) return Promise.resolve(cached);
        if (photoPromises[key]) return photoPromises[key];

        var titles = (LANDMARKS[key] || []).concat([city]);
        var p = titles.reduce(function (chain, title) {
            return chain.then(function (found) { return found || byTitle(title); });
        }, Promise.resolve(null)).then(function (found) {
            return found || bySearch(city + " " + countryName(country) + " city");
        }).then(function (url) {
            if (url) cacheSet(ck, url);
            return url;
        });
        photoPromises[key] = p;
        return p;
    }
    function thumbSize(url, px) {
        return /\/thumb\//.test(url) ? url.replace(/\/\d+px-/, "/" + px + "px-") : url;
    }

    function loadHeroPhoto(root) {
        var img = document.getElementById("cityBackgroundImg");
        var bg = document.getElementById("weatherHeroBg");
        if (!img) return Promise.resolve();
        return resolveCityPhoto(root.getAttribute("data-city"), root.getAttribute("data-country")).then(function (url) {
            if (!url) { if (bg) bg.classList.add("no-photo"); return; }
            var pre = new Image();
            pre.onload = function () {
                img.src = url;
                img.classList.add("is-loaded");
                if (bg) bg.classList.add("has-photo");
                var credit = document.getElementById("heroPhotoCredit");
                if (credit) credit.hidden = false;
            };
            pre.onerror = function () { if (bg) bg.classList.add("no-photo"); };
            pre.src = url;
        });
    }
    function loadChipPhotos() {
        var chips = document.querySelectorAll(".chip-city-icon[data-city]");
        Array.prototype.forEach.call(chips, function (el) {
            resolveCityPhoto(el.getAttribute("data-city"), el.getAttribute("data-country")).then(function (url) {
                if (!url) return;
                var small = thumbSize(url, 330);
                var pre = new Image();
                pre.onload = function () { el.style.backgroundImage = "url('" + small + "')"; el.classList.add("has-photo"); };
                pre.src = small;
            });
        });
    }

    /* ---------------------------------------------------------------------
       5. Count-up numbers
       --------------------------------------------------------------------- */
    function countUp(el) {
        var txt = el.textContent.trim();
        var m = /^(-?\d+(?:\.\d+)?)(.*)$/.exec(txt);
        if (!m) return;
        var target = parseFloat(m[1]), suffix = m[2];
        var dec = (m[1].split(".")[1] || "").length;
        var dur = 1100, t0 = null;
        function frame(ts) {
            if (t0 === null) t0 = ts;
            var p = clamp((ts - t0) / dur, 0, 1), e = 1 - Math.pow(1 - p, 3);
            el.textContent = (target * e).toFixed(dec) + suffix;
            if (p < 1) requestAnimationFrame(frame); else el.textContent = txt;
        }
        el.textContent = (0).toFixed(dec) + suffix;
        requestAnimationFrame(frame);
    }

    /* ---------------------------------------------------------------------
       Boot
       --------------------------------------------------------------------- */
    function init() {
        swapIcons();
        loadChipPhotos();

        var root = document.querySelector("[data-weather-fx]");
        if (!root) return;

        var cond = parseCondition(root.getAttribute("data-icon"), root.getAttribute("data-desc"), root.getAttribute("data-wind"));
        root.setAttribute("data-fx", cond.type);
        root.setAttribute("data-night", cond.night ? "true" : "false");
        document.body.setAttribute("data-fx", cond.type);

        // Hero card + sky panel get the full effect; the whole page gets a subtle ambient layer.
        startFX(document.getElementById("heroFx"), cond, {});
        startFX(document.getElementById("skyFx"), cond, {});
        var page = document.createElement("canvas");
        page.id = "pageFx"; page.className = "fx-page"; page.setAttribute("aria-hidden", "true");
        document.body.insertBefore(page, document.body.firstChild);
        startFX(page, cond, { ambient: true });

        loadHeroPhoto(root);

        var title = document.getElementById("current-weather-heading");
        if (title) {
            var tm = /^(.*),\s*([A-Za-z]{2})\s*$/.exec(title.textContent.trim());
            if (tm && countryName(tm[2]) !== tm[2]) title.textContent = tm[1] + ", " + countryName(tm[2]);
        }

        var upd = document.getElementById("heroUpdated");
        if (upd) {
            var d = new Date();
            upd.textContent = "Updated " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        }
        if (!reduceMotion) {
            Array.prototype.forEach.call(document.querySelectorAll(".temp-value, .hero-metric-value"), countUp);
        }
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();

    window.WeatherLabUI = { iconSVG: iconSVG, parseCondition: parseCondition, resolveCityPhoto: resolveCityPhoto };
})();
