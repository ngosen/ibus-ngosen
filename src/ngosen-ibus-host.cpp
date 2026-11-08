/*
 * SPDX-FileCopyrightText: 2026 Ngó Sen contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "ngosen-ibus-host.h"

#include "ngosen-app-quirks.h"
#include "ngosen-ibus-shell.h"
#include "ngosen-keysym.h"
#include "ngosen-log.h"
#include "ngosen-xtest.h"

#include <algorithm>
#include <libintl.h>

namespace ngosen {

    static_assert(key::BackSpace == IBUS_KEY_BackSpace);
    static_assert(key::Return == IBUS_KEY_Return);
    static_assert(key::space == IBUS_KEY_space);
    static_assert(key::Shift_L == IBUS_KEY_Shift_L);
    static_assert(modifier::Ctrl == IBUS_CONTROL_MASK);

    std::atomic<bool> clicksWatched{false};

    namespace {
        // IBus keycodes are evdev codes: KEY_BACKSPACE, KEY_TAB, KEY_RIGHT, KEY_LEFTSHIFT, KEY_ENTER.
        constexpr guint BackSpaceKeycode = 14;
        constexpr guint TabKeycode       = 15;
        constexpr guint RightKeycode     = 106;
        constexpr guint ShiftKeycode     = 42;
        constexpr guint ReturnKeycode    = 28;

        constexpr guint SimpleModifiers = IBUS_SHIFT_MASK | IBUS_CONTROL_MASK | IBUS_MOD1_MASK | IBUS_MOD4_MASK | IBUS_SUPER_MASK | IBUS_HYPER_MASK | IBUS_META_MASK;

        class GlibTimer final : public Timer {
          public:
            GlibTimer(uint64_t deadlineUs, std::function<bool(Timer&)> onTime) : onTime_(std::move(onTime)) {
                source_                                   = g_source_new(&funcs_, sizeof(Source));
                reinterpret_cast<Source*>(source_)->timer = this;
                g_source_set_ready_time(source_, static_cast<gint64>(deadlineUs));
                g_source_attach(source_, nullptr);
            }
            ~GlibTimer() override {
                g_source_destroy(source_);
                g_source_unref(source_);
            }
            GlibTimer(const GlibTimer&)            = delete;
            GlibTimer& operator=(const GlibTimer&) = delete;

            void       rearm(uint64_t deadlineUs) override {
                g_source_set_ready_time(source_, static_cast<gint64>(deadlineUs));
            }

          private:
            struct Source {
                GSource    base;
                GlibTimer* timer;
            };

            static gboolean dispatch(GSource* base, GSourceFunc /*callback*/, gpointer /*data*/) {
                auto* timer = reinterpret_cast<Source*>(base)->timer;
                // Fires once unless the callback rearms it and returns true.
                g_source_set_ready_time(base, -1);
                if (!timer->onTime_(*timer))
                    g_source_set_ready_time(base, -1);
                return G_SOURCE_CONTINUE;
            }

            static GSourceFuncs         funcs_;
            GSource*                    source_ = nullptr;
            std::function<bool(Timer&)> onTime_;
        };

        GSourceFuncs GlibTimer::funcs_ = {nullptr, nullptr, &GlibTimer::dispatch, nullptr, nullptr, nullptr};
    } // namespace

    void IBusHost::commitText(const std::string& text) {
        ibus_engine_commit_text(engine_, ibus_text_new_from_string(text.c_str()));
    }

    // Kept apart from the copy IBus edits on each deletion: GNOME Shell turns a deletion into bytes on
    // the text the app last reported, so that is the copy the core counts on.
    void IBusHost::setReportedText(const gchar* text, guint cursor, guint anchor) {
        const auto length = static_cast<guint>(g_utf8_strlen(text, -1));
        reported_         = cursor <= length && anchor <= length ? Surrounding(text, cursor, anchor) : Surrounding();
    }

    void IBusHost::forwardKey(EditKey key, bool release, uint32_t /*time*/) {
        const guint state = release ? IBUS_RELEASE_MASK : 0;
        switch (key) {
            case EditKey::BackSpace: ibus_engine_forward_key_event(engine_, IBUS_KEY_BackSpace, BackSpaceKeycode, state); break;
            case EditKey::Right: ibus_engine_forward_key_event(engine_, IBUS_KEY_Right, RightKeycode, state); break;
            case EditKey::Shift: ibus_engine_forward_key_event(engine_, IBUS_KEY_Shift_L, ShiftKeycode, state); break;
            case EditKey::Return: ibus_engine_forward_key_event(engine_, IBUS_KEY_Return, ReturnKeycode, state); break;
            case EditKey::ShiftReturn: ibus_engine_forward_key_event(engine_, IBUS_KEY_Return, ReturnKeycode, state | IBUS_SHIFT_MASK); break;
            case EditKey::Tab: ibus_engine_forward_key_event(engine_, IBUS_KEY_Tab, TabKeycode, state); break;
            case EditKey::ShiftTab: ibus_engine_forward_key_event(engine_, IBUS_KEY_ISO_Left_Tab, TabKeycode, state | IBUS_SHIFT_MASK); break;
        }
    }

    // The core counts X11 keycodes, which are evdev codes plus 8.
    void IBusHost::forwardKeyPress(uint32_t sym, uint32_t states, uint32_t code, bool release, uint32_t /*time*/) {
        const guint keycode = code >= 8 ? code - 8 : 0;
        ibus_engine_forward_key_event(engine_, sym, keycode, states | (release ? IBUS_RELEASE_MASK : 0));
    }

    void IBusHost::deleteSurrounding(int offset, unsigned int size) {
        ibus_engine_delete_surrounding_text(engine_, offset, size);
    }

    // The core presses keys only where forwarded ones do not reach the app, as with fcitx5.
    bool IBusHost::pressSystemKeys(int count) {
        if (xtestAvailable())
            return xtestSendKeys(count);
        return takesSentKeyEvents(field()) && xsendKeys(count);
    }

    Surrounding IBusHost::surrounding() const {
        if (throughShell())
            return reportsText() ? reported_ : Surrounding();
        // The Shell applies a deletion to the text last reported, not to the copy IBus edits itself.
        if (client_ == "gnome-shell")
            return field().surroundingText ? reported_ : Surrounding();
        if ((engine_->client_capabilities & IBUS_CAP_SURROUNDING_TEXT) == 0)
            return {};
        IBusText* text   = nullptr;
        guint     cursor = 0;
        guint     anchor = 0;
        ibus_engine_get_surrounding_text(engine_, &text, &cursor, &anchor);
        if (text == nullptr)
            return {};
        Surrounding copy(ibus_text_get_text(text), cursor, anchor);
        g_object_unref(text);
        return copy;
    }

    // Only GNOME Shell may drop the keys an engine forwards; X11 apps delete with BackSpace as usual.
    bool IBusHost::throughShell() const {
        return direct_ && client_ == "gnome-shell";
    }

    // Not every app resets on a click (XIM clients never do), and IBus text comes too late to check.
    bool IBusHost::seesCursorMoves() const {
        return clicksWatched.load(std::memory_order_acquire);
    }

    bool IBusHost::typesWithKeysBesideText() const {
        return direct_ && !throughShell() && (engine_->client_capabilities & IBUS_CAP_SURROUNDING_TEXT) != 0;
    }

    // Where GNOME Shell drops forwarded keys nothing could correct a copy behind the app, so the field
    // counts as reporting nothing and types with the preedit.
    bool IBusHost::reportsText() const {
        return client_ == "gnome-shell" && (engine_->client_capabilities & IBUS_CAP_SURROUNDING_TEXT) != 0 && shellDeliversKeys();
    }

    Field IBusHost::field() const {
        Field f;
        // As for an IBus client of fcitx5, so the checks in ngosen-app-quirks.cpp apply as they are.
        f.frontend = "ibus";
        // The Shell names every app it relays after itself, so the rules for one app need its own name.
        f.program = client_ == "gnome-shell" && !shellFocusedApp().empty() ? shellFocusedApp() : client_;
        if (f.program != client_)
            f.reportedProgram = client_;
        f.surroundingText = throughShell() ? reportsText() : (engine_->client_capabilities & IBUS_CAP_SURROUNDING_TEXT) != 0;
        f.preedit         = (engine_->client_capabilities & IBUS_CAP_PREEDIT_TEXT) != 0;
        f.url             = purpose_ == IBUS_INPUT_PURPOSE_URL;
        f.terminal        = purpose_ == IBUS_INPUT_PURPOSE_TERMINAL;
        // Outside GNOME Shell only a click watcher tells a click from a reset; Chromium and Electron report
        // no text and show the preedit well.
        if (direct_ && !throughShell() && !clicksWatched.load(std::memory_order_acquire))
            f.surroundingText = false;
        // Address bars keep the preedit and terminals erase with DEL, whatever the Shell does with keys.
        const bool shellKeys   = throughShell() && reportsText() && !f.url && !f.terminal;
        const bool preeditOnly = (throughShell() && !shellKeys) || (direct_ && !f.surroundingText);
        f.sendsNoKeys          = preeditOnly;
        f.preeditFallback      = preeditOnly && f.preedit;
        // With the underline or in English the Shell still drops forwarded keys, but deleting through the
        // text reaches the app, so an edit of committed text goes that way. The Shell maps it onto the text
        // last reported: a field with none, a terminal or an address bar's selected completion would go wrong.
        if (!direct_ && client_ == "gnome-shell" && !shellDeliversKeys()) {
            f.sendsNoKeys = true;
            if (f.terminal || f.url || !reported_.isValid())
                f.surroundingText = false;
        }
        f.password = purpose_ == IBUS_INPUT_PURPOSE_PASSWORD || purpose_ == IBUS_INPUT_PURPOSE_PIN || (hints_ & IBUS_INPUT_HINT_PRIVATE) != 0;
        return f;
    }

    bool IBusHost::hasFocus() const {
        return focus_;
    }

    // IBus gives an engine no access to the X11 selection.
    std::optional<std::string> IBusHost::takeSelection() {
        return std::nullopt;
    }

    void IBusHost::showPreedit(const std::string& text, bool /*underline*/) {
        preedit_ = text;
    }

    void IBusHost::clearPreedit() {
        preedit_.clear();
    }

    void IBusHost::resetPanel() {
        preedit_.clear();
        status_.clear();
        hideCandidates();
    }

    void IBusHost::refreshPreedit() {
        IBusText*   text   = ibus_text_new_from_string(preedit_.c_str());
        const guint length = static_cast<guint>(g_utf8_strlen(preedit_.c_str(), -1));
        // Some apps draw a preedit without attributes as plain text, which looks already typed.
        if (length > 0)
            ibus_text_append_attribute(text, IBUS_ATTR_TYPE_UNDERLINE, IBUS_ATTR_UNDERLINE_SINGLE, 0, length);
        // The app commits the preedit itself when it resets or loses focus, so no word is lost.
        ibus_engine_update_preedit_text_with_mode(engine_, text, length, length > 0, IBUS_ENGINE_PREEDIT_COMMIT);
    }

    void IBusHost::refreshPanel() {
        showTable();
        showAuxiliary();
    }

    // The core refreshes the panel on every key, so the table goes out only when it changed.
    void IBusHost::showTable() {
        if (menuOpen_ || (!tableDirty_ && tableShown_ == list_.has_value()))
            return;
        tableDirty_ = false;
        if (!list_) {
            if (tableShown_)
                ibus_engine_hide_lookup_table(engine_);
            tableShown_ = false;
            return;
        }
        IBusLookupTable* table = ibus_lookup_table_new(static_cast<guint>(list_->pageSize), static_cast<guint>(list_->cursor), TRUE, FALSE);
        ibus_lookup_table_set_orientation(table, IBUS_ORIENTATION_VERTICAL);
        // No labels of its own: the core numbers the candidates it lets the user pick by number.
        for (const auto& label : list_->labels)
            ibus_lookup_table_append_candidate(table, ibus_text_new_from_string(label.c_str()));
        ibus_engine_update_lookup_table(engine_, table, TRUE);
        tableShown_ = true;
    }

    void IBusHost::showAuxiliary() {
        const std::string& text = status_.empty() ? notice_ : status_;
        ibus_engine_update_auxiliary_text(engine_, ibus_text_new_from_string(text.c_str()), !text.empty());
    }

    void IBusHost::setMenuOpen(bool open) {
        menuOpen_ = open;
        // The menu takes the table; candidates still shown go out again on the next refresh.
        if (open) {
            tableShown_ = false;
            tableDirty_ = true;
        }
    }

    void IBusHost::showNotice(const std::string& text) {
        notice_ = text;
        showAuxiliary();
    }

    void IBusHost::hideNotice() {
        notice_.clear();
        showAuxiliary();
    }

    void IBusHost::showCandidates(const std::vector<std::string>& labels, int pageSize, std::function<void(size_t)> onPick) {
        tableDirty_ = true;
        if (labels.empty()) {
            list_.reset();
            return;
        }
        // IBus aborts on a page of more than 16.
        list_ = CandidateList{labels, std::clamp(pageSize, 1, 16), 0, std::move(onPick)};
    }

    void IBusHost::hideCandidates() {
        list_.reset();
        tableDirty_ = true;
    }

    std::optional<CandidatePage> IBusHost::candidates() const {
        if (!list_)
            return std::nullopt;
        CandidatePage page;
        page.total    = static_cast<int>(list_->labels.size());
        page.pageSize = list_->pageSize;
        page.cursor   = list_->cursor;
        page.page     = list_->cursor / list_->pageSize;
        page.hasPrev  = page.page > 0;
        page.hasNext  = (page.page + 1) * page.pageSize < page.total;
        return page;
    }

    void IBusHost::highlightCandidate(int index) {
        if (list_ && index >= 0 && index < static_cast<int>(list_->labels.size())) {
            list_->cursor = index;
            tableDirty_   = true;
        }
    }

    // The panel shows the page with the highlight, so a new page highlights its first candidate.
    void IBusHost::nextCandidatePage() {
        if (const auto page = candidates(); page && page->hasNext)
            highlightCandidate((page->page + 1) * page->pageSize);
    }

    void IBusHost::prevCandidatePage() {
        if (const auto page = candidates(); page && page->hasPrev)
            highlightCandidate((page->page - 1) * page->pageSize);
    }

    void IBusHost::pickCandidate(int index) {
        if (!list_ || index < 0 || index >= static_cast<int>(list_->labels.size()))
            return;
        // The callback may hide or replace the list it belongs to.
        const auto onPick = list_->onPick;
        if (onPick)
            onPick(static_cast<size_t>(index));
    }

    void IBusHost::clickCandidate(guint indexInPage) {
        if (const auto page = candidates())
            pickCandidate(page->page * page->pageSize + static_cast<int>(indexInPage));
    }

    void IBusHost::setStatus(const std::string& text) {
        status_ = text;
    }

    std::string IBusHost::translate(const char* text) const {
        return dgettext("ibus-ngosen", text);
    }

    std::unique_ptr<Timer> IBusHost::startTimer(uint64_t deadlineUs, uint64_t /*accuracyUs*/, std::function<bool(Timer&)> onTime) {
        return std::make_unique<GlibTimer>(deadlineUs, std::move(onTime));
    }

    std::string IBusHost::keyText(uint32_t sym) const {
        const gunichar c = ibus_keyval_to_unicode(sym);
        if (c == 0)
            return {};
        char      buf[6];
        const int n = g_unichar_to_utf8(c, buf);
        return std::string(buf, static_cast<size_t>(n));
    }

    uint32_t IBusKeyPress::sym() const {
        return sym_;
    }

    uint32_t IBusKeyPress::states() const {
        return state_ & IBUS_MODIFIER_MASK & ~IBUS_RELEASE_MASK;
    }

    bool IBusKeyPress::isRelease() const {
        return (state_ & IBUS_RELEASE_MASK) != 0;
    }

    bool IBusKeyPress::isModifier() const {
        return (sym_ >= IBUS_KEY_Shift_L && sym_ <= IBUS_KEY_Hyper_R) || sym_ == IBUS_KEY_ISO_Level3_Shift || sym_ == IBUS_KEY_ISO_Level5_Shift;
    }

    bool IBusKeyPress::isBareShift() const {
        return (sym_ == IBUS_KEY_Shift_L || sym_ == IBUS_KEY_Shift_R) && (state_ & SimpleModifiers & ~IBUS_SHIFT_MASK) == 0;
    }

    // The typing logic compares X11 keycodes, which are evdev codes plus 8.
    uint32_t IBusKeyPress::code() const {
        return code_ + 8;
    }

    // IBus passes no timestamp to the engine.
    uint32_t IBusKeyPress::time() const {
        return 0;
    }

    bool IBusKeyPress::hasModifier() const {
        return (state_ & SimpleModifiers) != 0;
    }

    bool IBusKeyPress::isCursorMove() const {
        switch (appSym_) {
            case IBUS_KEY_Left:
            case IBUS_KEY_Right:
            case IBUS_KEY_Up:
            case IBUS_KEY_Down:
            case IBUS_KEY_Page_Up:
            case IBUS_KEY_Page_Down:
            case IBUS_KEY_Home:
            case IBUS_KEY_End: return (state_ & SimpleModifiers & ~(IBUS_CONTROL_MASK | IBUS_SHIFT_MASK)) == 0;
            default: return false;
        }
    }

    std::string IBusKeyPress::name() const {
        std::string out;
        if ((state_ & IBUS_CONTROL_MASK) != 0)
            out += "Control+";
        if ((state_ & IBUS_MOD1_MASK) != 0)
            out += "Alt+";
        if ((state_ & IBUS_SHIFT_MASK) != 0)
            out += "Shift+";
        if ((state_ & (IBUS_MOD4_MASK | IBUS_SUPER_MASK)) != 0)
            out += "Super+";
        const gchar* keyName = ibus_keyval_name(appSym_);
        return keyName != nullptr ? out + keyName : std::string();
    }

    void IBusKeyPress::replaceSym(uint32_t sym) {
        appSym_ = sym;
    }

    void IBusKeyPress::accept() {
        accepted_ = true;
    }

    bool IBusKeyPress::accepted() const {
        return accepted_;
    }

} // namespace ngosen
