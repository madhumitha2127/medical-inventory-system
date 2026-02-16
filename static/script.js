function showSection(id){

    document.querySelectorAll(".section").forEach(sec=>{
        sec.style.display="none";
    });

    document.getElementById(id).style.display="block";
    if(id === "stock"){
    loadTablets();
}

if(id === "analytics"){
    loadSales();
}

if(id === "bills"){
    loadBills();
}

}

function showToast(message, type="success"){

    const toast = document.getElementById("toast");

    // convert \n into line breaks
    toast.innerHTML = message.replace(/\\n/g,"<br>");

    toast.className = "show toast-" + type;

    setTimeout(()=>{
        toast.className = toast.className.replace("show","");
    },3000);
}


async function loadTablets(){
    const response = await fetch("/tablets");
    const tablets = await response.json();

    let output = "";


    if(tablets.length === 0){
        output += "<p>No tablets available.</p>";
    } else {
           tablets.forEach(t => {

           let color = "#eaffea"; // green

         if(t.status === "EXPIRED"){
        color = "#ffe6e6"; // red
    }

    output += `
        <div class="tablet" style="background-color:${color}">
            💊 <b>${t.name}</b><br>
            Qty: ${t.qty}<br>
            Expiry: ${t.expiry}<br>
            Status: ${t.status}
        </div>
    `;
    })
    document.getElementById("tabletList").innerHTML = output;
}
}

async function addTablet(){
    const name = document.getElementById("name").value;
    const qty = document.getElementById("qty").value;
    const expiry = document.getElementById("expiry").value;

    const response = await fetch("/add-tablet", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name, qty, expiry})
    });

    const result = await response.json();
    if(result.error){
    showToast(result.error,"error");
}
else{
    showToast(result.message,"success");
}


    loadTablets();
}
async function sellTablet(){

    const name = document.getElementById("sellName").value;
    const qty = document.getElementById("sellQty").value;
    const price = document.getElementById("sellPrice").value;

    const response = await fetch("/sell-tablet",{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body: JSON.stringify({
            name,
            qty,
            price
        })
    });

    const result = await response.json();

    if(result.error){
    showToast(result.error,"error");
}
else{
    showToast(result.message,"success");
}


    loadTablets(); // refresh inventory
}
async function loadSales(){

    const response = await fetch("/sales");
    const data = await response.json();

    document.getElementById("salesData").innerHTML = `
        <h2>Sales Analytics</h2>
        💰 Revenue: ${data.total_revenue} <br>
        📦 Items Sold: ${data.total_items_sold} <br>
        🏆 Most Sold: ${data.most_sold_tablet}
    `;
}
async function checkAlerts(){

    const response = await fetch("/alerts");
    const data = await response.json();

    let message = "";

    if(data.expired.length > 0){
        message += "⚠️ Expired Tablets:\\n" + data.expired.join(", ") + "\\n\\n";
    }

    if(data.out_of_stock.length > 0){
        message += "📦 Out of Stock:\\n" + data.out_of_stock.join(", ");
    }

    if(message !== ""){
        showToast(message,"warning");

    }
}

async function loadBills(){

    const response = await fetch("/bills");
    const bills = await response.json();

    let output = "<h2>Billing History</h2>";

    if(bills.length === 0){
        output += "<p>No bills found.</p>";
    }
    else{

        bills.forEach(b => {

    output += `
        <div style="
            background:white;
            margin:10px;
            padding:10px;
            border-radius:8px;
            box-shadow:0 0 5px rgba(0,0,0,0.1);
        ">

        🧾 <b>Bill ID:</b> ${b.bill_id} <br>
        💊 <b>Tablet:</b> ${b.tablet} <br>
        📦 <b>Qty:</b> ${b.qty} <br>
        💰 <b>Total:</b> ${b.total} <br><br>

        <b>QR Code:</b><br>
        <img src="${b.qr}" width="120">

        </div>
    `;
});

    }

    document.getElementById("billList").innerHTML = output;
}
document.addEventListener("DOMContentLoaded", loadTablets);



