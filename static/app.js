// alert("in js!")

// function upcount() {
//     alert("in funct");
//     upcount = document.getElementById("upCount").innerHTML.value + 1;
//     alert(upcount)
//     document.getElementById("upCount").innerHTML.value = upcount;
// }


// fetch("http://127.0.0.1:5000/receiver", 
//  {
//  method: 'POST',
//  headers: {
//  'Content-type': 'application/json',
//  'Accept': 'application/json'
//  },
//  // Strigify the payload into JSON:
//  body:JSON.stringify(cars)}).then(res=>{
//  if(res.ok){
//  return res.json()
//  }else{
//  alert("something is wrong")
//  }
//  }).then(jsonResponse=>{
 
//  // Log the response data in the console
//  console.log(jsonResponse)
//  } 
//  ).catch((err) => console.error(err));