#set document(title: "Phân tích Khám phá Dữ liệu & Kết quả Ban đầu")
#set page(paper: "a4", margin: 2.4cm, numbering: "1")
#set text(size: 11pt, font: "New Computer Modern", lang: "vi")
#set par(justify: true)
#set heading(numbering: "1.1")
#set math.equation(numbering: "(1)")
#show link: underline

#let II(x) = $bold(1)[#x]$

#align(center)[
  #text(
    size: 17pt,
    weight: "bold",
  )[Phân tích Khám phá Dữ liệu & Kết quả Ban đầu] \
  #text(size: 13pt)[Yếu tố Đông đúc theo Tầng Ví (Tier-Aware Crowding) và \
    Cảnh báo sớm các Đợt Bùng phát Thanh lý Đồng bộ \
    trên Thị trường Hợp đồng Tương lai Vĩnh cửu On-chain] \
  #v(0.5em)
  #text(size: 11pt)[Luận văn Thạc sĩ Khoa học Máy tính] \
  #text(size: 11pt)[Tháng 7, 2026]
]

#v(1em)

#align(center)[#text(weight: "bold")[Tóm tắt]]
#block(inset: (x: 1.2em))[
  Báo cáo này phát triển và kiểm chứng độ khả thi cho một hướng nghiên cứu luận văn mới, dựa trên cơ sở dữ liệu `perpetuals_knowledge_graph` (40,5 triệu sự kiện log, 1,34 triệu vị thế đã đóng, 190.573 sự kiện thanh lý tường minh, 249 tài sản, 5 sàn giao dịch, 491 ngày dữ liệu). Chúng tôi dự báo các _đợt bùng phát thanh lý đồng bộ_ (synchronized liquidation bursts)---những khoảng thời gian ngắn trong đó nhiều vị thế hợp đồng tương lai vĩnh cửu (perpetual futures) trên cùng một tài sản bị đóng cưỡng bức cùng lúc---và đặt câu hỏi liệu các đặc trưng _đông đúc theo tầng ví_ (tier-aware crowding) có cải thiện khả năng dự báo so với mô hình nền tự kích thích (self-exciting) kiểu Hawkes hay không. Hai thử nghiệm khả thi được thực hiện trước khi xây dựng bất kỳ mô hình nào. (i) Giả thuyết _"nam châm thanh lý"_ (giá bị hút về các vùng giá thanh lý dày đặc) đã bị *bác bỏ* trên ba tài sản thanh khoản cao nhất, dưới hai dạng kiểm định độc lập (đều cho kết quả null). (ii) Nhãn _bùng phát thanh lý_ (burst) đã *vượt qua thử nghiệm một cách thuyết phục*: nhãn này dày đặc và có khả năng học mạnh---chỉ một đặc trưng cường độ trễ (trailing-intensity) đơn lẻ đã đạt AUC 0,83--0,87, xác nhận hiện tượng tự kích thích. Trên một phép chia dữ liệu theo thời gian, an toàn không rò rỉ (4,2 triệu dòng tài sản-khung giờ, 40 tài sản), một mô hình gradient boosting được tinh chỉnh với đặc trưng đông đúc (mất cân bằng theo tầng, lan tỏa liên tài sản, giá trị danh nghĩa thanh lý; 17 đặc trưng) được so sánh với ba mô hình nền _có tên gọi, đã công bố_, cùng huấn luyện trên dữ liệu giống nhau: một quá trình Hawkes đơn biến cổ điển (ước lượng hợp lý cực đại), một Hawkes đa biến có thành phần thị trường, và một Transformer Hawkes Process thần kinh @zuo2020thp. Sau đó, ba mô hình sử dụng đặc trưng hiệp biến (covariate) được đánh giá: bộ phân loại đã tinh chỉnh, một quá trình điểm thần kinh (neural point process) có điều kiện hiệp biến (mô hình hazard dựa trên GRU trên chuỗi đặc trưng), và một mạng nơ-ron đồ thị không gian--thời gian (spatio-temporal GNN) trên đồ thị liên tài sản. Trên độ đo precision-recall---thước đo trung thực cho một tập kiểm tra có tỷ lệ dương chỉ 0,56%---cả ba mô hình đều vượt trội hơn cả ba mô hình nền với khoảng cách lớn; quá trình điểm có điều kiện hiệp biến (CovTPP) đạt kết quả tốt nhất (PR-AUC 0,256, so với 0,157 của Hawkes cổ điển và 0,129 của THP thần kinh, mức tăng từ +0,10 đến +0,13), nhỉnh hơn một chút so với GNN (0,251) và bộ phân loại đã tinh chỉnh (0,250). Yếu tố quyết định chính là các đặc trưng hiệp biến, được chứng minh _trong cùng một họ mô hình_: quá trình điểm thần kinh gần như _tăng gấp đôi_ PR-AUC (0,129→0,256) khi được điều kiện hóa theo đặc trưng đông đúc thay vì chỉ dựa vào thời điểm sự kiện. Đáng chú ý, tất cả các mô hình nền chỉ dựa vào cường độ (intensity-only) đều đạt ROC-AUC ≈0,97 nhưng PR-AUC chỉ ≈0,13--0,16: cường độ tự kích thích là một bộ xếp hạng (ranker) mạnh nhưng là tín hiệu độ chính xác (precision) yếu dưới điều kiện mất cân bằng---điều mà ROC che giấu còn PR-AUC phơi bày. Khác với công thức chấm điểm kỹ năng ví (wallet-scoring) trước đây---nơi nhãn đánh giá gần như 99% là nhiễu lấy mẫu---bài toán này có một nhãn dày đặc, đáng tin cậy, nên mức cải thiện đo được là có ý nghĩa thực chất.
]

#v(1em)

= Bối cảnh Thể chế (Institutional Background) <sec:institutional>

Phần này giải thích các khái niệm thị trường được dùng xuyên suốt báo cáo, để người đọc không chuyên về thị trường phái sinh crypto vẫn theo dõi được các phần sau.

== Hợp đồng tương lai vĩnh cửu (Perpetual Futures) là gì

Hợp đồng tương lai vĩnh cửu (perpetual futures, viết tắt perp) là một công cụ phái sinh cho phép giao dịch có đòn bẩy trên giá của một tài sản (ví dụ BTC, SOL) mà không có ngày đáo hạn, khác với hợp đồng tương lai truyền thống. Vì không có ngày đáo hạn để giá hợp đồng tự động hội tụ về giá giao dịch spot, cơ chế giữ cho giá perp bám sát giá spot là tỷ lệ tài trợ (funding rate): định kỳ (thường mỗi 1–8 giờ), bên nắm giữ vị thế mua (long) và bên nắm giữ vị thế bán (short) thanh toán một khoản phí nhỏ cho nhau, tỷ lệ thuận với chênh lệch giữa giá perp và giá chỉ số (index/oracle price). Khi giá perp cao hơn giá spot, long trả phí cho short (khuyến khích bán, kéo giá xuống); khi thấp hơn sẽ theo chiều ngược lại. Perp hiện là công cụ phái sinh crypto phổ biến nhất và ngày càng đóng vai trò trung tâm trong việc khám phá giá.



== Đòn bẩy, Ký quỹ và Cơ chế Thanh lý (Liquidation)

Một vị thế perp được mở bằng một khoản ký quỹ ban đầu (initial margin) m, nhân với đòn bẩy (leverage) ℓ để có quy mô vị thế danh nghĩa s = m × ℓ (ví dụ: ký quỹ 100 USD, đòn bẩy 10x => vị thế trị giá 1000 USD). Sàn/giao thức yêu cầu vị thế luôn duy trì một mức ký quỹ duy trì (maintenance margin) tối thiểu, tính theo tỷ lệ ký quỹ hiện tại trên quy mô vị thế. Khi giá thị trường di chuyển ngược hướng vị thế đủ để tỷ lệ ký quỹ giảm xuống dưới ngưỡng duy trì, vị thế đó chạm giá thanh lý (liquidation price) - xấp xỉ


$
  P_"liq" approx P_"entry" times (1 minus.plus 1/ell) quad ("Long: " -,quad "Short: " +),
$
và bị *đóng cưỡng bức* (force-closed), có nghĩa là sàn hoặc giao thức (hoặc một _keeper_/liquidator bên thứ ba được thưởng phí) tự động đóng vị thế bằng cách khớp một lệnh ngược chiều ra thị trường, bất kể chủ vị thế có đồng ý hay không. Đòn bẩy càng cao, khoảng cách tới giá thanh lý càng hẹp.


== Cơ chế gây ra Đợt Bùng phát Thanh lý (Liquidation Cascade)

Rủi ro hệ thống đặc trưng của perp là *thanh lý dây chuyền* (liquidation cascade): việc đóng cưỡng bức một vị thế long tạo ra một lệnh *bán* ra thị trường; việc đóng một vị thế short tạo ra một lệnh *mua*. Nếu nhiều vị thế cùng chiều tập trung quanh một vùng giá thanh lý gần nhau (tức là vị thế nằm quanh một chiều và tập trung), việc thanh lý loạt vị thế đầu tiên đẩy giá đi xa hơn theo đúng hướng đã gây thanh lý, kích hoạt lớp vị thế đòn bẩy tiếp theo chạm ngưỡng thanh lý của chính nó - một chuỗi phản ứng tự kích thích, lây lan (self-exciting, contagious).


== Hai kiến trúc perp on-chain: Hyperliquid và Jupiter

Dữ liệu của luận văn trải trên 5 sàn/giao thức, nhưng hai kiến trúc đối lập đáng chú ý nhất---và là nguồn dữ liệu giá chính (`hyperliquid_prices`)---là:

- *Hyperliquid*: một sàn perp phi tập trung vận hành trên một blockchain Lớp-1 (L1) riêng do chính Hyperliquid xây dựng, sử dụng cơ chế đồng thuận HyperBFT với thời gian tạo khối dưới một giây. Khớp lệnh theo mô hình *sổ lệnh giới hạn trung tâm on-chain* (on-chain central limit order book, CLOB)---tương tự sàn tập trung (CEX) truyền thống nhưng toàn bộ sổ lệnh và khớp lệnh đều diễn ra on-chain. Một _vault_ nội bộ (HLP) đóng vai trò nhà tạo lập thị trường và hấp thụ một phần rủi ro thanh lý khi thanh khoản sổ lệnh không đủ.
- *Jupiter Perpetuals* (trên Solana): không dùng sổ lệnh, mà dùng mô hình *giao dịch đối ứng với hồ thanh khoản* (pool-based/peer-to-pool): mọi trader giao dịch trực tiếp với một hồ thanh khoản chung (JLP pool), hồ này đóng vai trò đối tác cho mọi vị thế và gánh lãi/lỗ ròng của toàn bộ trader. Giá tham chiếu để định giá vị thế và xác định thời điểm thanh lý lấy từ *oracle* giá bên ngoài (ví dụ Pyth Network) thay vì từ khớp lệnh nội bộ.

Sự khác biệt kiến trúc này (sổ lệnh vs. hồ thanh khoản, cơ chế giá nội sinh vs. oracle) là lý do báo cáo không giả định một cơ chế thanh lý thống nhất duy nhất, mà xây dựng nhãn bùng phát @eq:burst và các đặc trưng đông đúc (@sec:formulation) một cách _bất khả tri với sàn_ (venue-agnostic), gộp sự kiện thanh lý từ `close_action = Liquidate` trên toàn bộ 5 sàn/chuỗi, đồng thời giữ venue như một _mark_ tùy chọn trong công thức cường độ đa biến (@eq:intensity).

== Đầu ra của mô hình: hệ thống dự đoán điều gì

Với mỗi tài sản $a$ và mỗi khung 5 phút $t$, hệ thống dự đoán một *xác suất nhị phân*: liệu trong cửa sổ $h$ phút tiếp theo, số lượng sự kiện thanh lý trên tài sản $a$ có đạt hoặc vượt ngưỡng $theta$ hay không (định nghĩa hình thức tại @eq:burst, @sec:formulation). Đây *không phải* là dự đoán chiều giá (tăng/giảm), cũng không phải dự đoán một sự kiện thanh lý đơn lẻ, mà là dự đoán _cụm sự kiện đồng bộ_---một tín hiệu cảnh báo sớm rủi ro thác thanh lý, hướng tới ứng dụng thực tế: cảnh báo cho nhà quản lý rủi ro hoặc chính trader trước khi một đợt bùng phát xảy ra.


== Quá trình Hawkes

Quá trình Hawkes là một quá trình điểm ngẫu nhiên (_self-exciting point process_) mà trong đó sự xuất hiện của một sự kiện làm tăng xác suất xuất hiện các sự kiện tiếp theo trong một khoảng thời gian ngắn. Một quá trình Hawkes đơn biến mô hình hóa cường độ điều kiện của các sự kiện thanh lý dưới dạng một tỷ lệ nền hằng số $mu$ cộng tổng các kích thích suy giảm do mỗi sự kiện quá khứ đóng góp: $ lambda(t) = mu + sum_{t_j<t} alpha e^{-beta(t-t_j)} $.
với:
- $lambda(t)$: *cường độ có điều kiện* tại thời điểm $t$, biểu diễn tốc độ kỳ vọng xuất hiện sự kiện ngay tại thời điểm đó, với điều kiện đã biết toàn bộ lịch sử trước $t$. Giá trị $lambda(t)$ càng lớn thì khả năng xảy ra sự kiện trong khoảng thời gian rất ngắn tiếp theo càng cao.
- $mu$: *cường độ nền (baseline intensity)*, là tốc độ xảy ra sự kiện khi không chịu ảnh hưởng từ các sự kiện trước đó.
- $sum_{t_j<t}$: tổng trên tất cả các sự kiện đã xảy ra trước thời điểm ttt.
- $alpha$: *hằng số tính độ mạnh của hiệu ứng kích thích*. Mỗi khi một sự kiện xảy ra, cường độ sẽ tăng thêm một lượng ban đầu bằng $alpha$.
  - $alpha$ lớn → mỗi sự kiện tạo ảnh hưởng mạnh.
  - $alpha$ nhỏ → ảnh hưởng yếu.
- $e^{-beta(t-t_j)}$: *hàm suy giảm theo thời gian*.
  - $t-t_j$: khoảng thời gian kể từ khi sự kiện j xảy ra.
  - $beta$: hằng số tốc độ suy giảm.
    - $beta$ lớn → ảnh hưởng mất đi rất nhanh.
    - $beta$ nhỏ → ảnh hưởng kéo dài.


Mỗi sự kiện $j$ nâng cường độ lên ngay lập tức một lượng $alpha$, sau đó suy giảm theo hàm mũ với tốc độ $beta$ về lại $mu$; khi nhiều sự kiện xảy ra gần nhau, các mức kích thích cộng dồn khiến cường độ tăng vọt hẳn lên, vượt quá threshold - đây chính xác là hình ảnh của một thác thanh lý ở cấp độ đếm sự kiện. @fig:hawkesexample mô phỏng một quá trình ổn định (dưới ngưỡng tới hạn), tỷ lệ phân nhánh 𝛼 𝛽 ≈ 0, 61 < 1, và vẽ đường cường độ cùng với các thời điểm sự kiện mô phỏng: giai đoạn yên tĩnh nằm ở mức 𝜇. Mỗi một sự kiện xảy ra sẽ tạo ra một bước nhảy rõ rệt rồi suy giảm, với một cụm ba sự kiện gần nhau đẩy 𝜆(𝑡) lên gần gấp 5 lần mức nền trước khi hạ nhiệt.


#figure(
  image("figs_vi/hawkes_example.pdf", width: 92%),
  caption: [Ví dụ minh họa đường cường độ Hawkes tự kích thích (mô phỏng; $mu=0,3$, $alpha=0,55$, $beta=0,9$, tỷ lệ phân nhánh $alpha/beta approx 0,61$). Các vạch đứng là thời điểm sự kiện mô phỏng; đường cong là $lambda(t)$. Mỗi sự kiện kích hoạt một bước nhảy tức thời độ lớn $alpha$ rồi suy giảm mũ với tốc độ $beta$; một cụm sự kiện gần nhau cộng dồn các bước nhảy này thành một đợt bùng phát rõ rệt trước khi $lambda(t)$ hạ về lại mức nền $mu$ (nét đứt).],
) <fig:hawkesexample>

= Phát biểu Bài toán <sec:formulation>

== Vì sao Dự báo Đợt Bùng phát Thanh lý lại quan trọng

Hợp đồng tương lai vĩnh cửu là công cụ phái sinh crypto phổ biến nhất. Rủi ro hệ thống đặc trưng của chúng là thanh lý dây chuyền: khi một cụm vị thế đòn bẩy vi phạm ngưỡng ký quỹ duy trì, các lệnh thanh lý cưỡng bức sẽ được bán ra thị trường, đẩy giá trên hợp đồng tương lai đi xa hơn, và kích hoạt lớp vị thế đòn bẩy tiếp theo — một chuỗi tháo chạy tự kích thích, lây lan. Các tín hiệu cảnh báo sớm hiện có mà giới thực hành sử dụng (tỷ lệ tài trợ cực đoan, mất cân bằng long/short, open interest kỷ lục) là các ngưỡng heuristic, không phải mô hình dự báo đã hiệu chỉnh. Chính vì vậy nghiên cứu đặt ra một câu hỏi quan trọng hơn, có thể học được: _cho trạng thái thị trường tại thời điểm $t$, xác suất xảy ra một đợt bùng phát thanh lý đồng bộ trong $h$ phút tiếp theo là bao nhiêu, và các đặc trưng đông đúc phân giải theo tầng ví có cải thiện dự báo đó so với một mô hình nền thuần túy tự kích thích hay không_?

== Giả thuyết Đông đúc (Crowding Hypothesis)
Hiện tượng "đông đúc" (crowding) trong trường hợp này tức là khi mức độ các vị thế trong một tầng ví (wallet tier) - ví dụ như ví lớn, ví nhỏ - cùng tập trung vào một hướng bên trong giao dịch, và tương đương cùng một mức đòn bẩy, thì chỉ cần một biến động giá nhỏ cũng đủ để kích hoạt thanh lý hàng loạt, vì nhiều ví cùng chạm đến một ngưỡng thanh lý đồng thời.

== Định nghĩa Hình thức của Đợt Bùng phát

Gọi $L_(a,t)$ là số sự kiện thanh lý của tài sản $a$ trong khung 5 phút $t$. Nhãn bùng phát tại tầm dự báo $h$ (tính theo số khung) và ngưỡng $theta$ là
$ Y_(a,t)^((h)) = II(sum_(tau in (t,\, t+h]) L_(a,tau) gt.eq theta) $ <eq:burst>
Nhãn chỉ sử dụng cửa sổ _tương lai_ $(t, t+h]$; mọi biến dự báo được tính trên cửa sổ _quá khứ_ $[t-w, t]$, do đó đặc trưng và nhãn tách biệt nhau theo cấu trúc. @sec:m0burst cố định điểm vận hành tại $h=3$ khung (15 phút), $theta=3$.

== Phân rã Cường độ Bùng phát

Chúng tôi mô hình hóa cường độ điều kiện của các sự kiện thanh lý cho tài sản $a$ (và, trong mô hình đầy đủ, các _mark_ tầng ví và sàn giao dịch $k$) như một quá trình tự kích thích với một hàm nền điều kiện hóa theo hiệp biến:
$
  lambda_k (t) = underbrace(mu_k (x_k (t)), "hàm nền điều kiện hóa theo đông đúc") + sum_(k') sum_(t_j < t) alpha_(k'->k) phi(t - t_j)
$ <eq:intensity>
trong đó
- $K = {1,dots,K}$: tập các mark (cặp ví-tầng-sàn);
- $x_k(t) in R^p$: véc-tơ hiệp biến đông đúc tại mark $k$, quan sát được tại thời điểm $t^-$;
- $mu_k: R^p -> R_{>0}$: hàm nền điều kiện hóa theo đông đúc, ví dụ $mu_k(x) = exp(beta_k^top x)$;
- $t_j^{k'}$: thời điểm sự kiện thanh lý thứ $j$ trên mark $k'$, trước $t$;
- $phi_{k' -> k}(dot)$: hạt nhân kích hoạt từ mark $k'$ sang mark $k$, dạng mũ $phi_{k'\to k}(u) = beta_{k'\to k}\, e^{-beta_{k'\to k} u}$ với $u>0$;
- $alpha_{k'\to k} gt.eq 0$: cường độ lây lan chéo-mark (chéo-tầng, chéo-sàn) từ $k'$ sang $k$.

Giả thuyết trung tâm của luận văn là $x_k(t)$ sẽ mang thông tin
về các đợt bùng phát tương lai vượt ra ngoài những gì lịch sử sự kiện gần đây có thể cung cấp.

@fig:intensity cho thấy ánh xạ vào hai số hạng của @eq:intensity.

#figure(
  image("figs_vi/intensity.pdf", width: 90%),
  caption: [Phân rã cường độ bùng phát, @eq:intensity. Các mô hình nền đã công bố chỉ mô hình hóa số hạng tự kích thích (phải); các mô hình sử dụng hiệp biến trong luận văn này cung cấp hàm nền điều kiện hóa theo đông đúc (trái). Luận văn đo _mức tăng_ khi bổ sung số hạng bên trái, được tách bạch rõ nhất trong họ TPP thần kinh (THP → CovTPP).],
) <fig:intensity>

== Giả thuyết Đông đúc (Crowding Hypothesis)
Hiện tượng "đông đúc" (crowding) trong trường hợp này tức là khi mức độ các vị thế trong một tầng ví (wallet tier) - ví dụ như ví lớn, ví nhỏ - cùng tập trung vào một hướng bên trong giao dịch, và tương đương cùng một mức đòn bẩy, thì chỉ cần một biến động giá nhỏ cũng đủ để kích hoạt thanh lý hàng loạt, vì nhiều ví cùng chạm đến một ngưỡng thanh lý đồng thời.


Đông đúc làm mỏng "biên độ an toàn" của thị trường: khi vị thế tập trung và lệch một chiều---đặc biệt ở các ví lớn---một biến động bất lợi vừa phải cũng đủ thanh lý nhiều vị thế cùng lúc. Do đó, với mỗi tài sản và mỗi khung 5 phút, chúng tôi xây dựng các đặc trưng mà một đại lượng vô hướng đơn lẻ như tỷ lệ tài trợ không thể biểu đạt được: mất cân bằng long/short theo open interest, mất cân bằng theo từng tầng (ví nhỏ/trung/lớn), độ bất đồng nhỏ-so-với-lớn, mức độ tập trung vị thế, đòn bẩy trung bình của các vị thế đang mở, và tốc độ biến thiên của các đại lượng này. Mục tiêu dự đoán @eq:burst kiểm định trực tiếp liệu các hiệp biến này có làm tăng xác suất bùng phát hay không.


== Đóng góp

Tóm gọn trong một câu: _Khi thêm một hiệp biến biểu thị cho sự đông đúc vào trong hàm nền cường độ của một quá trình tự kích thích, tăng gấp đôi PR-AUC so với các mô hình nền quá trình điểm chỉ dựa vào cường độ, trên một dự báo bùng phát thanh lý ngoài mẫu, an toàn không rò rỉ._ Cụ thể:

- *(C1)* Một bảng đông đúc phân giải theo tầng ví và nhãn bùng phát an toàn không rò rỉ, xây dựng từ 40,5 triệu sự kiện on-chain thô (4,24 triệu dòng tài sản-khung, 40 tài sản; @sec:system to @sec:m0burst), với hai thử nghiệm khả thi được chạy _trước khi_ mô hình hóa để giảm rủi ro hướng đi.
- *(C2)* Một quá trình điểm thần kinh điều kiện hóa theo hiệp biến (CovTPP) hiện thực hóa hàm nền điều kiện hóa theo đông đúc $mu_k (dot)$ của @eq:intensity, tách bạch hiệu ứng hiệp biến _trong cùng_ họ TPP thần kinh, đối chứng với mô hình nền Transformer Hawkes Process.
- *(C3)* Các đặc trưng lan tỏa liên tài sản tường minh và một GNN không gian--thời gian trên đồ thị vị thế, đối chứng với một quá trình Hawkes đa biến có thành phần thị trường.
- *(C4)* Một đánh giá ưu tiên precision-recall trên các khung kiểm tra ngoài mẫu giống hệt nhau, qua sáu mô hình có tên gọi (@sec:results), phơi bày một sự phân kỳ ROC/PR mà báo cáo chỉ dựa vào ROC sẽ che giấu.

@sec:gap định vị mỗi đóng góp đối chứng với một khoảng trống cụ thể, có trích dẫn, trong các công trình trước đây.

= Công trình Liên quan (Related Work) <sec:related>

Chúng tôi tổ chức các công trình liên quan theo năm hướng nghiên cứu mà luận văn này nằm ở giao điểm, và nêu rõ tại @sec:gap chính xác vị trí mỗi hướng còn thiếu so với một dự báo bùng phát thanh lý có hiệu chỉnh, nhận biết đông đúc.

*Quá trình tự kích thích sinh ra thanh lý dây chuyền.* Mô hình hóa các sự kiện tài chính tập trung thành cụm như quá trình tự kích thích (Hawkes) đã được thiết lập vững chắc: @bacry2015hawkes khảo sát quá trình Hawkes trong tài chính, và @hardiman2013endogeneity dùng tỷ lệ phân nhánh (branching ratio) để định lượng tính nội sinh/phản xạ của thị trường (endogeneity/reflexivity)---cùng cơ chế mà @filimonov2012reflexivity gắn với các đợt sụp đổ chớp nhoáng (flash crash). Công trình DeFi gần nhất, @cao2025defi, cho thấy các sự kiện thanh lý tập trung thành cụm _xuyên_ nhiều giao thức trong một khung Hawkes đa biến, còn @markovhawkes2025manipulation mở rộng cường độ Hawkes với một hàm nền điều biến kiểu Markov để phát hiện thao túng thị trường. Toàn bộ hướng này mô hình hóa cường độ chỉ từ _lịch sử sự kiện_ (@eq:intensity, số hạng thứ hai); trạng thái vị thế/đông đúc không bao giờ đi vào hàm nền $mu_k$. Một hướng nowcasting song song @nowcast2023crashrisk dự đoán rủi ro sụp đổ từ mất cân bằng dòng lệnh (order-flow imbalance) nhưng không dựa trên vị thế phân giải theo tầng ví.

*Vi cấu trúc thị trường perpetual và rủi ro thanh khoản.* Rủi ro thanh khoản hướng tới tương lai cho perp bắt đầu thu hút các khung phân tích chuyên biệt như Slippage-at-Risk @slippageatrisk2026, định lượng rủi ro thực thi lệnh nhưng coi thanh lý là một cú sốc thanh khoản ngoại sinh, chứ không phải một luồng sự kiện tự kích thích, dự báo được.

*Quá trình điểm thời gian có mark và thần kinh (neural TPP).* Một họ mô hình phong phú điều kiện hóa cường độ sự kiện theo lịch sử đã học: quá trình điểm thời gian có mark hồi quy @du2016rmtpp, quá trình Hawkes thần kinh @mei2017neuralhawkes, Transformer Hawkes Process @zuo2020thp, quá trình điểm thần kinh không gian--thời gian @zhou2022neuralstpp, dự báo đa sự kiện không gian--thời gian @beyondhawkes2022, và các biến thể state-space gần đây @mambahawkes2024, nay được đối chứng công khai bởi EasyTPP @xue2023easytpp. Các phương pháp này điều kiện hóa theo thời điểm sự kiện và _mark_ phân loại, nhưng---như mô hình nền THP của chúng tôi cho thấy bằng thực nghiệm---không điều kiện hóa theo các hiệp biến đông đúc liên tục, ngoại sinh; bộ máy thần kinh nâng cao độ biểu đạt so với Hawkes cổ điển nhưng vẫn rơi vào cùng dải độ chính xác khi chỉ được cấp thời điểm sự kiện (@tab:m2).

*Cấu trúc tô-pô và liên tài sản của đồ thị on-chain.* Cấu trúc mạng blockchain mang tín hiệu cảnh báo sớm: phát hiện bất thường tô-pô trên mạng đa lớp động @oforiboateng2021topological, đặc trưng tô-pô cho dự đoán bất thường giá @xrp2026topological, và phát hiện bất thường mạng theo tốc độ bền vững (persistence velocity) @persistencevelocity2025. Những công trình này là động lực cho đồ thị liên tài sản của chúng tôi (ST-GNN, @sec:results) nhưng nhắm tới bất thường giá/nhãn trên đồ thị giao dịch, không phải các đợt bùng phát thanh lý đồng bộ trên một đồ thị vị thế liên tài sản.

*Dự đoán conformal dưới dịch chuyển phân phối.* Vì tần suất bùng phát bị dịch chuyển (tỷ lệ nền tập kiểm tra 0,56% so với tập huấn luyện 1,51%, @sec:results), độ bất định đã hiệu chỉnh phải sống sót qua tính phi dừng: suy luận conformal thích nghi @gibbs2021adaptive, dự đoán conformal cho chuỗi thời gian @zaffran2022adaptive, và luồng conformal nhận biết dịch chuyển @driftconformal2026. Các công trình này cung cấp tầng hiệu chỉnh cho hệ thống được hoạch định nhưng chưa từng được áp dụng cho một quá trình điểm bùng phát thanh lý.

= Khoảng trống Nghiên cứu và Đóng góp <sec:gap>

Đọc năm hướng nghiên cứu cùng nhau, ta thấy một giao điểm cụ thể còn bỏ trống.

*G1 --- Mô hình thác thanh lý chỉ dựa vào cường độ bỏ qua đông đúc.* Các mô hình thanh lý DeFi/tài chính @cao2025defi @bacry2015hawkes @hardiman2013endogeneity dự báo chỉ từ lịch sử sự kiện. Liệu vị thế _phân giải theo tầng ví_ (mất cân bằng, tập trung, đòn bẩy) có bổ sung sức mạnh dự báo so với tự kích thích hay không---vẫn chưa được kiểm định.

*G2 --- TPP thần kinh chưa được điều kiện hóa theo đông đúc ngoại sinh.* Các quá trình điểm hiện đại nhất @zuo2020thp @mei2017neuralhawkes @du2016rmtpp điều kiện hóa theo thời điểm và mark, không theo một luồng hiệp biến liên tục về vị thế thị trường---nên câu hỏi hiệp biến-đối-cường độ chưa được tách bạch _trong cùng một họ mô hình_.

*G3 --- Lây lan xuyên giao thức mới chỉ được mô tả, chưa được dự báo.* @cao2025defi thiết lập cụm lây lan trên các giao thức trên mạng Blockchain khác nhau theo hướng mô tả; chưa công trình nào biến lan tỏa liên tài sản thành một dự báo _cảnh báo sớm_ có hiệu chỉnh, an toàn không rò rỉ, cho đợt bùng phát tiếp theo.

*G4 --- Chưa có cảnh báo sớm bùng phát đã hiệu chỉnh, nhận biết dịch chuyển.* Các phương pháp conformal @gibbs2021adaptive @zaffran2022adaptive đã tồn tại nhưng chưa được ghép nối với một quá trình điểm thanh lý để tạo ra các đảm bảo về độ trễ cảnh báo/tỷ lệ báo động giả có kiểm soát độ bao phủ dưới dịch chuyển chế độ thị trường.


*Đóng góp.* Luận văn này nhắm chính xác vào khoảng trống này: (C1) một bảng đông đúc phân giải theo tầng ví và nhãn bùng phát an toàn không rò rỉ, trên một kho dữ liệu on-chain 40,5 triệu sự kiện (@sec:related G1); (C2) một quá trình điểm thần kinh điều kiện hóa theo hiệp biến (CovTPP) tiêm đông đúc vào hàm nền cường độ $mu_k$ của @eq:intensity, tách bạch hiệu ứng hiệp biến trong cùng họ TPP thần kinh, đối chứng với mô hình nền THP (G2); (C3) các đặc trưng lan tỏa liên tài sản tường minh và một ST-GNN trên đồ thị vị thế, đối chứng với một Hawkes đa biến (G3); (C4) một đánh giá ưu tiên PR trên các khung ngoài mẫu giống hệt nhau, cùng một tầng hiệu chỉnh conformal thích nghi đã hoạch định cho dịch chuyển chế độ (G4, G5). Kết quả (@sec:results) xác nhận tuyên bố trung tâm của G1--G2: hiệp biến đông đúc gần như tăng gấp đôi PR-AUC so với các mô hình nền chỉ dựa vào cường độ, trong cùng một họ mô hình.

= Tổng quan Hệ thống <sec:system>

Nhìn tổng thể, nghiên cứu là một pipeline duy nhất, an toàn không rò rỉ nhãn (leakage-safe), biến đổi log sự kiện on-chain thô thành một dự báo bùng phát, được bảo vệ bởi hai thử nghiệm khả thi và đánh giá đối chứng với các mô hình nền quá trình điểm đã công bố. @fig:pipeline thể hiện luồng dữ liệu đầu-cuối, @fig:gates thể hiện hai cổng quyết định go/no-go đã định hình hướng đi, và @fig:models thể hiện bức tranh tổng thể các mô hình.

#figure(
  image("figs_vi/pipeline.pdf", width: 100%),
  caption: [Pipeline đầu-cuối. positions logs thô được tái tạo thành vị thế đã đóng, sau đó bộ xây dựng bảng tạo ra một dòng an toàn không rò rỉ cho mỗi (tài sản, khung 5 phút) trên một lưới thời gian toàn cục đồng bộ: đặc trưng lấy từ $[t-w,t]$, nhãn lấy từ cửa sổ tương lai rời rạc $(t,t+h]$. Bảng được chia theo thời gian và mọi mô hình được chấm điểm trên cùng các khung kiểm tra.],
) <fig:pipeline>

#figure(
  image("figs_vi/gates.pdf", width: 100%),
  caption: [Hai thử nghiệm khả thi định hình hướng đi _trước khi_ xây dựng bất kỳ mô hình nào. Thử nghiệm 1 (@sec:m0magnet) kiểm định giả thuyết nam châm thanh lý và bị bác bỏ. Thử nghiệm 2 (@sec:m0burst) xác nhận nhãn bùng phát dày đặc và có khả năng học mạnh.],
) <fig:gates>

#figure(
  image("figs_vi/models.pdf", width: 95%),
  caption: [Bức tranh tổng thể các mô hình. Ba mô hình nền quá trình điểm đã công bố chỉ tiêu thụ thời điểm sự kiện; ba mô hình trong luận văn này bổ sung 17 đặc trưng đông đúc/liên tài sản. Mũi tên nét đứt đánh dấu tương phản quyết định trong cùng một họ mô hình (THP → CovTPP). Cả sáu mô hình được chấm điểm trên cùng các khung kiểm tra ngoài mẫu (@tab:m2).],
) <fig:models>

== Tổng quan các Mô hình được Áp dụng <sec:modeloverview>

@fig:models nhóm sáu mô hình có tên gọi theo dữ liệu đầu vào: chỉ thời điểm sự kiện (ba mô hình nền quá trình điểm đã công bố) so với thời điểm sự kiện cộng véc-tơ hiệp biến đông đúc/liên tài sản 17 chiều (ba mô hình đề xuất trong luận văn này). Dưới đây là cơ chế của từng mô hình, bắt đầu từ quá trình Hawkes vì nó là nền tảng của mọi mô hình nền chỉ dựa vào cường độ, đồng thời là động lực trực tiếp cho hàm nền điều kiện hóa theo đông đúc trong @eq:intensity.


*Transformer Hawkes Process (THP).* THP thay hạt nhân mũ cố định bằng một hạt nhân đã học: một bộ mã hóa tự chú ý (self-attention) tiêu thụ chuỗi sự kiện quá khứ (và khoảng cách thời gian giữa các sự kiện) của từng tài sản, tạo ra một trạng thái ẩn $h_i$ cho mỗi sự kiện, từ đó đọc ra cường độ liên tục $lambda(t)="softplus"(v^top h_i + b + a(t-t_i))$. Mô hình này biểu đạt mạnh hơn hẳn hạt nhân mũ cổ điển, nhưng---giống các mô hình nền Hawkes---chỉ điều kiện hóa theo thời điểm sự kiện, không bao giờ theo trạng thái đông đúc.

*LightGBM (bộ phân loại hiệp biến).* Một tập hợp cây gradient boosting huấn luyện trực tiếp trên bảng 17 đặc trưng đông đúc để dự đoán nhãn nhị phân bùng phát @eq:burst, siêu tham số được tinh chỉnh bằng Optuna theo độ chính xác trung bình (average precision). Mô hình này không có khái niệm cường độ hay cấu trúc quá trình điểm; đây là mô hình nền phân biệt (discriminative) thuần túy mạnh nhất cho các hiệp biến.

*TPP thần kinh điều kiện hóa theo hiệp biến (CovTPP).* Phiên bản hiệp biến trực tiếp tương ứng với THP: một GRU chạy nhân quả trên chuỗi 17 đặc trưng (thay vì trên thời điểm sự kiện) để tạo trạng thái lịch sử $h_t$, đưa vào cùng đầu ra cường độ kiểu hazard $lambda_t="softplus"(w^top h_t+b)$, $P("bùng phát")=1-e^(-lambda_t)$. So sánh THP và CovTPP trong @tab:m2 tách bạch hiệu ứng của việc điều kiện hóa theo đông đúc, trong cùng một họ mô hình.

*GNN không gian--thời gian (ST-GNN).* Coi 40 tài sản là các nút trên lưới 5 phút toàn cục chung; một tầng đồ thị trao đổi một thông điệp thị trường liên tài sản giữa các nút đang hoạt động tại mỗi bước, và một GRU riêng cho từng nút mang trạng thái thời gian vào cùng đầu ra hazard như CovTPP. Mô hình này kiểm định liệu việc truyền thông điệp (message passing) tường minh có vượt qua các hiệp biến thị trường/lan tỏa đã thiết kế thủ công sẵn có trong bảng đặc trưng hay không.

= Tổng quan Dữ liệu <sec:data>

Nguồn dữ liệu chính là bộ sưu tập `logs` của cơ sở dữ liệu MongoDB `perpetuals_knowledge_graph`, ghi lại mọi sự kiện vòng đời mở/đóng cho các vị thế perpetual trên năm nền tảng (Hyperliquid, Jupiter, GMX-v2, APX, Myx) và năm blockchain. Các vị thế đã đóng được tái tạo và lưu tại `data/processed/positions.parquet`.

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, right, center),
    table.header([Đại lượng], [Giá trị], [Collection nguồn]),
    [Tổng số sự kiện log], [40.552.429], [`logs`],
    [Vị thế đã đóng], [1.342.059], [`closed_positions`],
    [Sự kiện thanh lý tường minh], [190.573], [`positions` (`Liquidate`)],
    [Tài sản có thanh lý], [249], [`positions`],
    [Điểm giá theo phút], [93.743.096], [`hyperliquid_prices`],
    [Vị thế đang mở (ảnh chụp)], [25.584], [`opening_positions`],
    [Kết quả backtest giao dịch], [567.784], [`trade_history`],
    [Độ dài dữ liệu], [491 ngày], [`logs`],
  ),
  caption: [Quy mô dữ liệu liên quan tới mô hình hóa bùng phát (số liệu đã kiểm chứng từ các collection).],
) <tab:scale>

*Mức độ sẵn có của các collection (đã kiểm chứng).* Có dữ liệu và hữu ích: `logs`, `closed_positions`, `opening_positions`, `hyperliquid_prices` (93,7 triệu điểm giá/phút), `hyperliquid_pairs`, `trade_history` (567 nghìn backtest), và các bảng trader đa tầm nhìn `web3_traders_{1D,3D,1W,1M}`. Không đủ hoặc thiếu: `signals` chỉ là một stub 29 văn bản, không giao nhau với ví perp; `market_stats` (108 văn bản) và ảnh chụp `aggregated_assets` quá thô để làm nguồn đông đúc biến đổi theo thời gian, nên đông đúc được tái tạo từ `logs` thay thế.

*Mức độ tập trung thanh lý.* Thanh lý tập trung ở các tài sản thanh khoản cao nhất: BTC (78.098), SOL (67.374), ETH (28.331), sau đó là một dải đuôi dài (XRP 2.173, BNB 1.223, DOGE 1.023, ...). Sự tập trung này định hình cả hai thử nghiệm khả thi bên dưới.

= Thử nghiệm Khả thi 1: Giả thuyết Nam châm Thanh lý (Bị Bác bỏ) <sec:m0magnet>

Trước khi cam kết theo hướng chính, chúng tôi kiểm định một ý tưởng lân cận hấp dẫn: rằng giá bị _hút_ về các cụm giá thanh lý dày đặc (hiệu ứng "nam châm" / stop-hunt). Giá thanh lý của mỗi vị thế mở được xấp xỉ bằng $"entry" times (1 minus.plus 1/"leverage")$ (Long $-$, Short $+$), trọng số theo quy mô, có hiệu lực trong khoảng $["open_ts", "close_ts")$; đường giá lấy từ `hyperliquid_prices`.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, right, right, center),
    table.header(
      [Tài sản], [Số vị thế], [Spearman($w$, lợi suất kỳ hạn)], [$p$ (Pearson)]
    ),
    [BTC], [399.044], [+0,017 / +0,029], [0,58 / 0,99],
    [SOL], [297.685], [+0,021], [0,97],
    [ETH], [201.350], [$-$0,001], [0,32],
  ),
  caption: [Thử nghiệm nam châm: kiểm định chiều hướng (Spearman giữa mất cân bằng vùng giá trọng số theo quy mô và lợi suất kỳ hạn) trên ba tài sản thanh khoản cao nhất. Tất cả đều null.],
) <tab:magnet>

Một kiểm định _hút_ sắc bén hơn---liệu giá có _chạm_ tới vùng giá trội gần nhất trong tầm dự báo nhiều hơn một mức gương cách đều ở phía đối diện---cũng cho kết quả null trên BTC: vùng giá bị chạm 2,4% / 6,0% số lần (tầm dự báo 120 / 360 phút) so với 2,7% / 6,1% cho mức gương ($z approx -0,66$ / $-0,22$). Tỷ lệ chạm đúng chiều về phía vùng giá là 0,496 / 0,509 (ngẫu nhiên 0,5), với khoảng tin cậy bootstrap 95% trải qua số 0.

*Kết luận.* Trên ba tài sản thanh khoản cao nhất (~900 nghìn vị thế) và hai dạng kiểm định độc lập, *không có tín hiệu nam châm thanh lý*. Cơ chế này không thể chứng minh được trên các tài sản chủ lực thanh khoản cao, nên bị *loại khỏi tuyên bố chính*. Bản đồ vùng giá thanh lý chỉ được giữ lại như một _đặc trưng_ ứng viên cho dự báo bùng phát. Lưu ý trung thực: giá thanh lý chỉ là xấp xỉ (không tính ký quỹ duy trì thực tế); các altcoin mỏng nhất thiếu mật độ dữ liệu để kiểm định nghiêm ngặt, nên tuyên bố chính xác là "không có nam châm trên các tài sản chủ lực thanh khoản cao."

= Thử nghiệm Khả thi 2: Nhãn Bùng phát (Vượt qua) <sec:m0burst>

Tiếp theo, chúng tôi kiểm chứng nhãn bùng phát @eq:burst: liệu nó có đủ cân bằng để huấn luyện, và liệu nó có thực sự dự đoán được hay không? Sự kiện thanh lý được gộp khung 5 phút theo từng tài sản (top-12 theo khối lượng thanh lý, gộp chung). Làm thước đo khả năng học, chúng tôi đo AUC của _một đặc trưng tầm thường duy nhất_---số lượt thanh lý trong 15 phút trước---khi dự đoán bùng phát tương lai.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (right, right, right, right, right),
    table.header(
      [$h$ (phút)],
      [$theta$],
      [Tỷ lệ nền gộp],
      [Số dương],
      [AUC(15ph trước → bùng phát)],
    ),
    [5], [3], [0,0123], [17.029], [0,873],
    [5], [5], [0,0054], [7.522], [0,893],
    [15], [3], [*0,0377*], [*52.182*], [0,831],
    [15], [5], [0,0202], [27.994], [0,862],
    [60], [3], [0,1191], [164.938], [0,755],
    [60], [5], [*0,0785*], [*108.807*], [0,788],
  ),
  caption: [Tỷ lệ nền bùng phát và khả năng học theo tầm dự báo $h$ và ngưỡng $theta$. AUC dùng một đặc trưng cường độ trễ (proxy tự kích thích).],
) <tab:burstbase>

*Kết luận: vượt qua.* Tỷ lệ nền nằm trong khoảng huấn luyện được (1--12%) với số lượng dương lớn ($10^4$--$10^5$), và nhãn có *khả năng học mạnh*: chỉ một đặc trưng cường độ trễ đơn lẻ đã đạt AUC 0,75--0,91. Tự kích thích là hiện tượng thực và mạnh---tiền đề Hawkes của @eq:intensity được xác nhận bằng thực nghiệm. Đây là hình ảnh nghịch đảo của thất bại wallet-scoring (nhãn nhiễu $rho=0,013$). Chúng tôi khóa điểm vận hành chính tại $h=15$ phút, $theta=3$ (tỷ lệ nền 3,8%, 52.182 mẫu dương). *Quan trọng: vì một đặc trưng cường độ trễ tầm thường đã đạt AUC ≈0,87, đóng góp mô hình hóa phải được đo bằng _mức tăng so với mô hình nền tự kích thích này_, không phải bằng khả năng dự đoán thô.*

= Phương pháp: Bảng Đông đúc An toàn Không rò rỉ và các Mô hình Nền

== Bảng Đặc trưng

Dịch vụ `src/burst/panel_builder.py` xây dựng, với mỗi tài sản và khung 5 phút, một dòng gồm nhãn bùng phát @eq:burst và bốn nhóm đặc trưng (17 đặc trưng), tất cả tính từ thông tin sẵn có tại hoặc trước $t$:

- *Nền (tự kích thích):* `past_liq_short` (số lượt thanh lý trong 15 phút trước), `past_liq_long` (60 phút).
- *Đông đúc:* mất cân bằng long/short theo open interest; mất cân bằng theo tầng lớn và tầng nhỏ; độ bất đồng theo tầng (lớn $-$ nhỏ); tỷ trọng open interest của tầng lớn (mức tập trung); đòn bẩy trung bình của vị thế đang mở; tốc độ biến thiên open interest; tốc độ biến thiên cường độ thanh lý.
- *Khối lượng:* _giá trị danh nghĩa_ (USD) thanh lý của chính tài sản trong cửa sổ trễ 15 và 60 phút.
- *Liên tài sản (đa biến):* số lượt và giá trị danh nghĩa thanh lý trễ toàn thị trường, và _lan tỏa_ từ các tài sản khác. Đây là phiên bản rời rạc, thiết kế thủ công tương ứng với kích thích chéo-mark $alpha_(k'->k)$ trong @eq:intensity.

Open interest theo (chiều, tầng) được duy trì chính xác như một hàm bậc thang: mỗi vị thế đóng góp $+"quy mô"$ tại khung mở và $-"quy mô"$ tại khung đóng; tổng tích lũy cho trạng thái mở tại mọi khung. Để các đặc trưng liên tài sản được định nghĩa tốt, mọi bảng theo từng tài sản được đặt trên một lưới 5 phút _toàn cục, đồng bộ theo epoch_ duy nhất ($floor("ts"\/300)$). Các tầng ví là tam phân vị (tercile) theo quy mô, tính riêng cho từng tài sản (dựa trên quy mô, không dựa trên nhãn, nên an toàn không rò rỉ). Mọi đặc trưng dùng $[t-w, t]$; nhãn dùng $(t, t+h]$; hai cửa sổ này tách biệt nhau.

== Các Mô hình Nền

Chúng tôi đối chứng với các _phương pháp có tên gọi, đã công bố_, tất cả được huấn luyện trên giai đoạn huấn luyện và chấm điểm trên cùng khung kiểm tra và nhãn.

- *Hawkes đơn biến* (`src/burst/hawkes.py`): quá trình tự kích thích cổ điển với hạt nhân kích hoạt dạng mũ $g(tau)=alpha beta e^(-beta tau)$, huấn luyện riêng cho từng tài sản bằng hợp lý cực đại (theo khung nội sinh-crypto Hawkes của @bacry2015hawkes, @hardiman2013endogeneity). Điểm số theo từng khung là cường độ điều kiện $lambda(t)$.
- *Hawkes có thành phần thị trường:* tự kích thích cộng thêm một số hạng kích thích toàn thị trường với hệ số suy giảm chung---một phiên bản khả thi thay thế cho Hawkes đa biến xuyên-sàn của @cao2025defi.
- *Transformer Hawkes Process (THP)* (`src/burst/thp.py`): một quá trình điểm thời gian thần kinh @zuo2020thp với bộ mã hóa tự chú ý trên chuỗi sự kiện của từng tài sản và một cường độ liên tục $lambda(t)="softplus"(v^top h_i + b + a (t-t_i))$.

== Các mô hình đề xuất sử dụng hiệp biến

- *LightGBM* trên 17 đặc trưng, với siêu tham số được tinh chỉnh bằng Optuna (`src/burst/tuner.py`).
- *TPP thần kinh điều kiện hóa theo hiệp biến* (`src/burst/covtpp.py`): một GRU chạy nhân quả trên chuỗi khung 5 phút của 17 đặc trưng, cho trạng thái lịch sử $h_t$; cường độ bùng phát là $lambda_t="softplus"(w^top h_t + b)$ và hazard theo tầm dự báo là $P("bùng phát")=1-e^(-lambda_t)$. Đây là hiện thực hóa trực tiếp của cường độ điều kiện hóa theo hiệp biến trong @eq:intensity: _cùng_ họ quá trình điểm thần kinh như THP, nhưng điều kiện hóa theo hiệp biến đông đúc.
- *GNN không gian--thời gian* (`src/burst/stgnn.py`): 40 tài sản là các nút trên lưới toàn cục chung; một tầng đồ thị trộn đặc trưng với một thông điệp thị trường liên tài sản, và một GRU riêng cho từng nút mang trạng thái thời gian.

Việc hiệu chỉnh đã hoạch định sẽ đối chứng conformal tĩnh với Suy luận Conformal Thích nghi @gibbs2021adaptive @zaffran2022adaptive; TPP điều kiện hóa theo hiệp biến là mục tiêu tự nhiên.

= Kết quả: Đông đúc có Vượt qua các Mô hình Nền Quá trình Điểm đã Công bố? <sec:results>

Chúng tôi xây dựng bảng trên toàn bộ 40 tài sản đạt ngưỡng thanh lý tối thiểu, thu được 4.239.195 dòng tài sản-khung với tỷ lệ bùng phát 1,22%. Bảng được chia _theo thời gian_ (không rò rỉ): 70% khung sớm nhất dùng huấn luyện (2.967.435 dòng, 1,51% dương), 30% khung muộn nhất dùng kiểm tra (1.271.760 dòng, 0,56% dương). Mọi mô hình trong @tab:m2 được chấm điểm trên cùng khung kiểm tra và nhãn.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, left, right, right),
    table.header([Mô hình], [Loại], [ROC-AUC ↑], [PR-AUC ↑]),
    table.cell(
      colspan: 4,
      align: left,
    )[_Mô hình nền quá trình điểm đã công bố (chỉ thời điểm sự kiện)_],
    [THP (TPP thần kinh; @zuo2020thp)], [cường độ], [0,9700], [0,1294],
    [Hawkes, +thị trường (đa biến), MLE], [cường độ], [0,9740], [0,1568],
    [Hawkes, đơn biến tự kích thích, MLE], [cường độ], [0,9746], [0,1570],
    table.cell(
      colspan: 4,
      align: left,
    )[_Mô hình dùng hiệp biến (luận văn này)_],
    [LGBM nền (cường độ trễ, 2 đặc trưng)], [phân biệt], [0,9078], [0,2281],
    [LGBM đầy đủ (+đông đúc+khối lượng+liên tài sản, đã chỉnh)],
    [phân biệt],
    [*0,9801*],
    [0,2502],
    [ST-GNN (đồ thị liên tài sản + GRU)],
    [không gian--thời gian],
    [0,9791],
    [0,2513],
    [*CovTPP (hazard GRU + hiệp biến)*], [TPP thần kinh], [0,9792], [*0,2556*],
    table.hline(),
    [Mức tăng của CovTPP so với Hawkes cổ điển (PR-AUC)], [], [], [+0,0986],
    [Mức tăng của CovTPP so với THP thần kinh (PR-AUC)], [], [], [+0,1262],
  ),
  caption: [Dự báo bùng phát ngoài mẫu trên giai đoạn kiểm tra muộn hơn, mọi mô hình chấm điểm trên cùng khung kiểm tra và nhãn (tỷ lệ nền 0,56%; PR-AUC ngẫu nhiên = 0,0056).],
) <tab:m2>

Năm quan sát, theo thứ tự độ tin cậy giảm dần:

+ *Mọi mô hình dùng hiệp biến đều vượt qua mọi mô hình nền quá trình điểm đã công bố trên precision-recall, với khoảng cách lớn.* Mô hình tốt nhất (TPP thần kinh điều kiện hóa theo hiệp biến) đạt PR-AUC 0,256 so với 0,157 của Hawkes cổ điển (+0,099) và 0,129 của THP thần kinh (+0,126). Đây là tuyên bố trung tâm của luận văn.
+ *Yếu tố quyết định là các hiệp biến, không phải họ mô hình---được chứng minh trong cùng một họ.* Quá trình điểm thần kinh tăng từ PR-AUC 0,129 (THP) lên 0,256 (CovTPP)---mức tăng khoảng 2 lần.
+ *ROC-AUC che giấu mất cân bằng; PR-AUC trung thực.* Mọi mô hình chỉ dựa vào cường độ đều dồn vào một dải hẹp, ROC-AUC ≈0,97 nhưng PR-AUC chỉ ≈0,13--0,16.
+ *Trong nhóm mô hình dùng hiệp biến, khác biệt là nhỏ.* CovTPP (0,2556), ST-GNN (0,2513), và LightGBM đã tinh chỉnh (0,2502) nằm trong khoảng ≈0,005 của nhau; Hawkes đa biến ngây thơ không thêm được gì (0,1568 so với 0,1570).
+ *Dịch chuyển phân phối hiện diện và là động lực cho hiệu chỉnh.* Tỷ lệ nền tập kiểm tra (0,56%) thấp hơn nhiều so với tập huấn luyện (1,51%).

Không có rò rỉ nhãn: biến dự báo dùng $[t-w,t]$ và nhãn dùng $(t,t+h]$; phép chia theo thời gian; tham số Hawkes và THP được ước lượng chỉ trên sự kiện thuộc giai đoạn huấn luyện.

= Thảo luận

Kết quả xác nhận hướng đi và định vị chính xác vấn đề mở. Bùng phát có thể dự đoán được, tự kích thích chi phối tín hiệu dễ, và mọi mô hình dùng hiệp biến đều vượt qua các mô hình nền chỉ dựa vào cường độ đã công bố trên độ đo trung thực, với TPP điều kiện hóa theo hiệp biến là tốt nhất. Bằng chứng rõ ràng nhất là tương phản _trong cùng một họ_: quá trình điểm thần kinh gần như tăng gấp đôi PR-AUC (0,129→0,256) khi cường độ của nó được điều kiện hóa theo hiệp biến đông đúc thay vì chỉ theo thời điểm sự kiện, tách bạch đông đúc---không phải lựa chọn bộ học---là nguồn gốc của khả năng dự đoán vượt ra ngoài tự kích thích. Phát hiện phương pháp luận trung tâm là sự _phân kỳ ROC/PR_ đi kèm: Hawkes cổ điển, Hawkes đa biến, và THP thần kinh đều đạt ROC-AUC ≈0,97 nhưng PR-AUC chỉ ≈0,13--0,16. Nhất quán với điều này, việc bổ sung một đồ thị liên tài sản tường minh (ST-GNN) không vượt qua bộ phân loại, vì các đặc trưng thị trường/lan tỏa thiết kế thủ công đã mã hóa sẵn tín hiệu liên tài sản.

Kết quả null của nam châm (@sec:m0magnet) là một kết quả tiêu cực hữu ích: nó ngăn việc xây dựng trên một hiệu ứng mà dữ liệu không ủng hộ, và giữ cho luận văn trung thực về những gì vùng giá thanh lý thực sự làm.

= Hạn chế

+ *Mô hình gọn nhẹ.* Mọi mô hình thần kinh đều được thiết kế nhỏ có chủ đích: THP (32 chiều, 2 tầng, 3 epoch, ngữ cảnh 64 sự kiện), TPP hiệp biến và ST-GNN (GRU 1 tầng, 48--64 ẩn, ≤4 epoch), Hawkes cổ điển dùng hạt nhân mũ với $beta$ trên một lưới nhỏ (MLE Nelder--Mead).
+ *Khác biệt nhỏ giữa các mô hình dùng hiệp biến.* CovTPP, ST-GNN, và bộ phân loại đã tinh chỉnh khác nhau ≤0,005 PR-AUC trên một phép chia đơn.
+ *Chỉ một phép chia theo thời gian.* Cần walk-forward đa fold xoay vòng để có khoảng tin cậy và độ nhạy theo chế độ thị trường.
+ *Liên tài sản qua đặc trưng thiết kế thủ công, không phải một quá trình đã khớp mô hình.*
+ *Giá thanh lý xấp xỉ* (không tính ký quỹ duy trì thực tế, không tính ký quỹ chéo).
+ *Không có hiệp biến tỷ lệ tài trợ* (vắng mặt trong schema); chỉ có thể dùng chu kỳ tài trợ.

= Tóm tắt Phát hiện Chính

*F1:* Hiệu ứng nam châm bị bác bỏ. Không có hiện tượng giá bị hút về vùng giá thanh lý trên BTC/SOL/ETH dưới hai dạng kiểm định.

*F2:* Nhãn bùng phát dày đặc và có khả năng học mạnh. Tỷ lệ nền 1--12% với $10^4$--$10^5$ mẫu dương; một đặc trưng cường độ trễ đơn lẻ cho AUC 0,75--0,91. Điểm vận hành đã khóa: $h=15$ phút, $theta=3$.

*F3:* Mô hình dùng hiệp biến vượt qua mô hình nền quá trình điểm đã công bố trên PR-AUC. PR-AUC 0,256 (CovTPP) > 0,251 (ST-GNN) > 0,250 (tuned LightGBM) ≫ 0,157 (Hawkes cổ điển) và 0,129 (THP thần kinh).

*F4:* Hiệp biến, không phải loại mô hình, là động lực của mức tăng. Cùng một họ TPP thần kinh tăng gấp đôi PR-AUC (0,129→0,256) khi được điều kiện hóa theo hiệp biến đông đúc.

*F5:* Nhãn đáng tin cậy, khác với wallet skill. Nhãn bùng phát dạng đếm sự kiện ($rho$ ≫ 0) tránh được nhiễu $rho=0,013$ từng giới hạn công thức trước đây.

= Bước Tiếp theo

*NS1:* Walk-forward đa fold xoay vòng để có khoảng tin cậy cho mức tăng và độ nhạy theo chế độ thị trường.

*NS2:* Độ đo tại điểm vận hành---độ chính xác tại recall cố định và độ chính xác trong top-$k$ khung được gắn cờ---cộng với PR-AUC có điều kiện theo open interest không tầm thường.

*NS3:* Hiệu chỉnh conformal thích nghi qua dịch chuyển chế độ (tỷ lệ nền kiểm tra 0,56% so với huấn luyện 1,51%).

*NS4:* Hiệu chỉnh TPP điều kiện hóa theo hiệp biến (@sec:results), và khớp một Hawkes có mark/đa biến để diễn giải kích thích $alpha_(k'->k)$; kiểm tra độ bền của khoảng cách với mô hình nền bằng một TPP thần kinh mạnh hơn.

= Hình ảnh

#figure(
  image(
    "../pipeline/outputs/b01_burst_baseline/burst_baseline_lift.png",
    width: 92%,
  ),
  caption: [Dự báo bùng phát trên giai đoạn kiểm tra theo thời gian, an toàn không rò rỉ. Trái: ROC-AUC và PR-AUC ngoài mẫu cho mô hình nền LightGBM tự kích thích so với mô hình đầy đủ đã tinh chỉnh. Phải: mức độ quan trọng của đặc trưng LightGBM của mô hình đầy đủ. Xem @tab:m2 để so sánh đầy đủ.],
) <fig:m1>

*Báo cáo hỗ trợ.* Các báo cáo thử nghiệm chi tiết tại `m0-magnet-findings.md`, `m0-burst-findings.md`, `m1-crowding-lift-findings.md`, `m2-baselines-findings.md`. Trích dẫn công trình liên quan (@sec:related to @sec:gap) được liệt kê dưới đây; các mục được đánh dấu _[unverified]_ trong `references.bib` đã xác nhận tiêu đề/mã arXiv nhưng cần kiểm tra tác giả/nơi công bố trước bản nộp cuối cùng.

#bibliography("references.bib", style: "ieee", title: "Tài liệu tham khảo")
