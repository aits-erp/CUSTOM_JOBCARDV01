frappe.ui.form.on('Job Card', {
    refresh: function(frm) {
        console.log("test");
        frm.page.wrapper.off('click', '[data-label="Complete%20Job"]');
        
        frm.page.wrapper.on('click', '[data-label="Complete%20Job"]', function(e) {
            
            if (!frm.doc.sequence_id || !frm.doc.work_order) {
                return;
            }
            
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Job Card",
                    filters: {
                        work_order: frm.doc.work_order,
                        sequence_id: ["<", frm.doc.sequence_id]
                    },
                    fields: ["name", "sequence_id", "status"]
                },
                callback: function(r) {
                    console.log("test");

                    if (r.message && r.message.length) {

                        let incomplete = r.message.find(jc => jc.status !== "Completed");

                        if (incomplete) {

                            frappe.msgprint(
                                "Complete previous sequence before completing this Job Card."
                            );

                            e.preventDefault();
                            e.stopPropagation();
                        }

                    }

                }
            });

        });

    }
});