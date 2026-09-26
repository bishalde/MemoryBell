/* Builds the same SMS text as the server, for live previews.
   Mirrors milestone() in app/services/dates.py and _build_sms_message() in app/services/scheduler.py. */
(function () {
    var LONG_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

    function ordinal(n) {
        var s = (n % 100 >= 10 && n % 100 <= 20) ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] || 'th');
        return n + s;
    }

    function milestone(type, years) {
        if (!years || years < 1) return '';
        if (type === 'birthday') return 'turns ' + years;
        if (type === 'anniversary') return ordinal(years) + ' anniversary';
        return years + (years === 1 ? ' year' : ' years');
    }

    // Next yearly occurrence of month m / day d, counting today. Feb 29 falls on Feb 28 in non-leap years.
    function nextOccurrence(m, d) {
        var today = new Date(); today.setHours(0, 0, 0, 0);
        var make = function (y) {
            var dt = new Date(y, m - 1, d);
            return dt.getMonth() === m - 1 ? dt : new Date(y, m - 1, 28);
        };
        var next = make(today.getFullYear());
        if (next < today) next = make(today.getFullYear() + 1);
        return { date: next, days: Math.round((next - today) / 86400000) };
    }

    function dateLabel(dt) {
        return LONG_MONTHS[dt.getMonth()] + ' ' + String(dt.getDate()).padStart(2, '0') + ', ' + dt.getFullYear();
    }

    function countdown(days) {
        return days === 0 ? 'Today' : days === 1 ? 'Tomorrow' : 'In ' + days + ' days';
    }

    // o: { firstName, name, contact, type, offset, years, notes, number, dateLabel, wishTo }
    function smsText(o) {
        var label = { birthday: 'birthday', anniversary: 'anniversary' }[o.type] || 'event';
        var contact = o.contact || 'Someone special';
        var when = {
            0: ['TODAY', 'Don’t miss it!'],
            1: ['TOMORROW', 'Still time to prepare!'],
            3: ['in 3 days', 'Plan something special!'],
            7: ['in 1 week', 'Plenty of time to get ready!']
        }[o.offset] || ['in ' + o.offset + ' days', 'Mark your calendar!'];
        var tip = o.type === 'birthday' ? 'Send a wish or surprise them with a gift!'
            : o.type === 'anniversary' ? 'Plan something memorable together!'
            : 'Make sure you’re prepared!';
        var marks = milestone(o.type, o.years), marksLine = '';
        if (marks) {
            marksLine = o.type === 'birthday' ? contact + ' ' + marks + '!\n'
                : o.type === 'anniversary' ? 'It’s the ' + marks + '!\n'
                : 'It’s been ' + marks + '!\n';
        }
        return 'Hi ' + (o.firstName || 'there') + '!\n\n' +
            contact + '’s ' + label + ' is ' + when[0] + '!\n' +
            'Event: ' + (o.name || 'Your occasion') + '\n' +
            'Date: ' + (o.dateLabel || 'your date') + '\n' + marksLine + '\n' +
            (o.notes ? 'Note: ' + o.notes + '\n\n' : '') +
            (o.number ? 'Text or call ' + (o.contact || 'them') + ': ' + o.number + '\n\n' : '') +
            (o.wishTo && o.offset === 0 ? 'We\u2019re texting your message to ' + o.wishTo + ' today.\n\n' : '') +
            when[1] + ' ' + tip;
    }

    // Mirrors _build_recipient_message() in app/services/scheduler.py
    function wishText(o) {
        return (o.message || '') + '\n\n(Sent by ' + (o.fullName || 'you') + ' via MemoryBell)';
    }

    window.MemoryBellSMS = {
        wishText: wishText,
        ordinal: ordinal, milestone: milestone, nextOccurrence: nextOccurrence,
        dateLabel: dateLabel, countdown: countdown, smsText: smsText
    };
})();
